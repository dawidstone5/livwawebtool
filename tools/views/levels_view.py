# import neccessary functions, libraries, and packages
import logging
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from tools.views.api_code import get_or_create_forecast, training_data, model_version
from tools.models import ForecastResult

logger = logging.getLogger(__name__)

# How many days of real historical actuals (ending where the training data
# does) to always show on the chart, regardless of how far in the future the
# requested prediction is. Without this, a request far past the training
# data's end - which is the common case, since the model isn't retrained
# continuously - would never pull in any real historical data for context.
HISTORICAL_LOOKBACK_DAYS = 730


def _insert_gap_breaks(df, gap_days=2):
    """
    Insert a null-value row wherever consecutive dates skip more than
    gap_days, so Plotly draws a visible break instead of a misleading
    straight line across a period nobody has predicted yet.
    """
    if df.empty:
        return df
    records = df.to_dict('records')
    out = [records[0]]
    for prev, curr in zip(records, records[1:]):
        if (curr['Date'] - prev['Date']).days > gap_days:
            out.append({'Date': prev['Date'] + (curr['Date'] - prev['Date']) / 2, 'Lake_Level': None})
        out.append(curr)
    return pd.DataFrame(out)


def _load_context_series():
    """
    Build a Date/Lake_Level/source series spanning the last
    HISTORICAL_LOOKBACK_DAYS of real historical actuals plus every
    already-cached forecast (of any date range), tagged by source so the
    chart can render measured data and predicted data as visually distinct
    lines instead of one undifferentiated trend.
    """
    frames = []

    if training_data is not None:
        max_date_train = training_data['Date'].max()
        lookback_start = max_date_train - pd.Timedelta(days=HISTORICAL_LOOKBACK_DAYS)
        historical = training_data[
            (training_data['Date'] >= lookback_start) & (training_data['Date'] <= max_date_train)
        ][['Date', 'Lake_Level']].copy()
        if not historical.empty:
            historical['source'] = 'historical'
            frames.append(historical)

    cached_rows = ForecastResult.objects.filter(
        model_version=model_version,
    ).values_list('result', flat=True)
    for records in cached_rows:
        rows = [
            {'Date': r['Date'], 'Lake_Level': r['Lake_Level']}
            for r in records if 'Date' in r and 'Lake_Level' in r
        ]
        if rows:
            predicted = pd.DataFrame(rows)
            predicted['source'] = 'predicted'
            frames.append(predicted)

    if not frames:
        return pd.DataFrame(columns=['Date', 'Lake_Level', 'source'])

    combined = pd.concat(frames, ignore_index=True)
    combined['Date'] = pd.to_datetime(combined['Date'])
    # A date covered by both a historical actual and a cached prediction
    # (shouldn't normally happen - predictions only start after the training
    # data ends) keeps the historical value.
    combined['_priority'] = combined['source'].map({'historical': 0, 'predicted': 1})
    combined = combined.sort_values(['Date', '_priority']).drop_duplicates(subset='Date', keep='first')
    return combined.drop(columns='_priority').sort_values('Date').reset_index(drop=True)


def _clean_levels(series):
    """Unwrap the occasional length-1 list/array a cached JSON value can come
    back as, so Plotly gets plain floats."""
    return series.apply(lambda x: x[0] if isinstance(x, (list, np.ndarray)) and len(x) > 0 else x)


# function for plotting the results
def generate_plot(context_df, highlight_start=None, highlight_end=None):
    """
    Generate an interactive Plotly chart (as an embeddable HTML fragment)
    from the tagged context series (Date/Lake_Level/source). Real historical
    (measured) data and model-predicted data are drawn as two distinctly
    colored lines - red for measured, green for predicted - so it's clear
    which points are actual readings versus a forecast. highlight_start/
    highlight_end, if given, shade the exact range the user requested in a
    lighter background so it stands out against the surrounding trend.
    """
    try:
        fig = go.Figure()

        historical = context_df[context_df['source'] == 'historical'][['Date', 'Lake_Level']].sort_values('Date')
        predicted = context_df[context_df['source'] == 'predicted'][['Date', 'Lake_Level']].sort_values('Date')

        if not historical.empty:
            historical = _insert_gap_breaks(historical.reset_index(drop=True))
            fig.add_trace(go.Scatter(
                x=historical['Date'], y=_clean_levels(historical['Lake_Level']),
                mode='lines', name='Historical (measured)',
                line=dict(color='#e74c3c', width=2),
                connectgaps=False,
            ))

        if not predicted.empty:
            predicted = _insert_gap_breaks(predicted.reset_index(drop=True))
            fig.add_trace(go.Scatter(
                x=predicted['Date'], y=_clean_levels(predicted['Lake_Level']),
                mode='lines', name='Predicted',
                line=dict(color='#1abc9c', width=2),
                connectgaps=False,
            ))

        if highlight_start is not None and highlight_end is not None:
            fig.add_vrect(
                x0=highlight_start, x1=highlight_end,
                fillcolor='rgba(26, 188, 156, 0.12)',
                line_width=0,
                layer='below',
                annotation_text='Requested prediction',
                annotation_position='top left',
            )

        fig.update_layout(
            title='Water Levels: Trend & Requested Prediction',
            xaxis_title='Date',
            yaxis_title='Water Level (m)',
            template='plotly_white',
            hovermode='x unified',
            margin=dict(l=50, r=30, t=60, b=50),
            height=550,
            # Click-drag pans (translates the visible window) instead of the
            # Plotly default box-zoom, which rescales both axes at once and
            # can look like the axis labels "jump". Panning keeps the x-axis
            # and y-axis anchored at the plot's edges the same way, however
            # far you drag through the historical-to-predicted trend.
            dragmode='pan',
        )

        return fig.to_html(
            full_html=False,
            include_plotlyjs=False,
            config={'displaylogo': False, 'scrollZoom': True, 'responsive': True},
        )

    except Exception:
        logger.exception("Error generating water level plot")
        return None


# levels view function to handle requests for water levels
@login_required
def levels(request):
    """
    Handle water level prediction requests
    """
    context = {}

    # Determine template based on authentication
    if request.user.is_authenticated:
        template_name = 'base_usr.html'
    else:
        template_name = 'base_all.html'

    context['template_name'] = template_name

    if request.method == 'POST':
        try:
            # Get date inputs from form
            start_date = request.POST.get('reference_start', None)
            end_date = request.POST.get('reference_end', None)

            # Validate inputs
            if not start_date or not end_date:
                messages.error(request, "Please provide both start and end dates.")
                context['error_message'] = "Missing start date or end date"
                return render(request, "tools/water_levels.html", context)
            
            # Parse dates
            start_date = pd.to_datetime(start_date)
            end_date = pd.to_datetime(end_date)
            
            # Validate date range
            if start_date >= end_date:
                messages.error(request, "End date must be after start date.")
                context['error_message'] = "Invalid date range: End date must be after start date."
                return render(request, "tools/water_levels.html", context)
            
            # Set to first day of month
            start_date = start_date.replace(day=1)
            end_date = end_date.replace(day=1)

            # Prepare date dictionaries for forecast function
            start = {
                "year": start_date.year,
                "month": start_date.month,
                "day": start_date.day
            }
            end = {
                "year": end_date.year,
                "month": end_date.month,
                "day": end_date.day
            }

            # Generate forecast (reuses a cached prediction for the same date range)
            results = get_or_create_forecast(start, end, training_data)
            
            # Validate forecast results
            if not results or len(results) == 0:
                messages.warning(request, "No forecast results were generated. Please try a different date range.")
                context['error_message'] = "No forecast results returned. Please try again with different dates."
                return render(request, "tools/water_levels.html", context)

            # Convert results to DataFrame
            df = pd.DataFrame(results)

            # Ensure Date column exists and set as index
            if 'Date' not in df.columns:
                messages.error(request, "Forecast data is missing date information.")
                context['error_message'] = "Invalid forecast data structure."
                return render(request, "tools/water_levels.html", context)
            
            df['Date'] = pd.to_datetime(df['Date'])
            df.set_index('Date', inplace=True)

            # Standardize water level column name
            if 'Lake_Level' in df.columns:
                df.rename(columns={'Lake_Level': 'water_levels'}, inplace=True)
            elif 'water_levels' not in df.columns:
                messages.error(request, "Forecast data is missing water level information.")
                context['error_message'] = "No water level data in forecast results."
                return render(request, "tools/water_levels.html", context)

            # Build a continuous context series (recent history plus every
            # nearby already-cached forecast) so the chart shows an ongoing
            # trend, not just the isolated slice that was requested.
            context_df = _load_context_series()
            if context_df.empty:
                # Fall back to just the requested slice, tagged by whether
                # each date falls within the training data (historical) or
                # beyond it (predicted).
                max_date_train = training_data['Date'].max() if training_data is not None else pd.Timestamp.min
                context_df = df.reset_index().rename(columns={'water_levels': 'Lake_Level'})
                context_df['source'] = context_df['Date'].apply(
                    lambda d: 'historical' if d <= max_date_train else 'predicted'
                )

            # Generate plot, shading the exact requested range for contrast
            plot_html = generate_plot(
                context_df,
                highlight_start=start_date, highlight_end=end_date,
            )

            if plot_html:
                context.update({
                    "plot_html": plot_html,
                    "reference_start_date": start_date,
                    "reference_end_date": end_date,
                })
                messages.success(request, f"Water level prediction generated successfully for {start_date.strftime('%B %Y')} to {end_date.strftime('%B %Y')}.")

                # Stash a summary for the Reports tool to pull real data from
                request.session['last_levels_result'] = {
                    'start_date': start_date.strftime('%Y-%m-%d'),
                    'end_date': end_date.strftime('%Y-%m-%d'),
                    'min_level': float(df['water_levels'].min()),
                    'max_level': float(df['water_levels'].max()),
                    'mean_level': float(df['water_levels'].mean()),
                }
            else:
                messages.error(request, "Failed to generate the prediction chart. Please try again.")
                context['error_message'] = "Could not generate the results plot."

        except ValueError as e:
            messages.error(request, "Invalid date format. Please use the date picker.")
            context['error_message'] = f"Date parsing error: {str(e)}"
        
        except Exception as e:
            messages.error(request, "An unexpected error occurred while processing your request.")
            context['error_message'] = f"An error occurred: {str(e)}"
            print(f"Error in levels view: {str(e)}")  # Log for debugging

    return render(request, "tools/water_levels.html", context)