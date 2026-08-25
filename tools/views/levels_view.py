# import neccessary functions, libraries, and packages
import logging
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from tools.views.api_code import forecast, training_data

logger = logging.getLogger(__name__)


# function for plotting the results
def generate_plot(results_df, selected_variable):
    """
    Generate an interactive Plotly chart (as an embeddable HTML fragment) from
    the results dataframe. Zoom (scroll/box-select) and pan are Plotly defaults.
    """
    try:
        # Ensure the variable data is in the correct format
        results_df[selected_variable] = results_df[selected_variable].apply(
            lambda x: x[0] if isinstance(x, (list, np.ndarray)) and len(x) > 0 else x
        )

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=results_df.index,
            y=results_df[selected_variable],
            mode='lines',
            name='Water Levels',
            line=dict(color='#1abc9c', width=2),
        ))
        fig.update_layout(
            title='Predicted Water Levels over Time',
            xaxis_title='Date',
            yaxis_title='Water Level (m)',
            template='plotly_white',
            hovermode='x unified',
            margin=dict(l=50, r=30, t=60, b=50),
            height=450,
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

            # Generate forecast
            results = forecast(start, end, training_data)
            
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

            # Generate plot
            plot_html = generate_plot(df, 'water_levels')

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