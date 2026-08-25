import json
import logging
from io import BytesIO

import pandas as pd, numpy as np
from django.shortcuts import render
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseNotAllowed
import plotly.graph_objects as go
from reportlab.pdfgen import canvas as pdf_canvas

logger = logging.getLogger(__name__)

# =================================================================================================================

# __________________________________________________________________________________________________BIAS CORRECTION
def linear_scaling(observed, modeled):
    scale_factor = np.mean(observed) / np.mean(modeled)
    corrected = modeled * scale_factor
    return corrected
# ================================================================================================== linear scaling
def quantile_mapping(observed, modeled):
    idx = observed.index
    observed = observed.to_numpy().flatten()
    modeled = modeled.to_numpy().flatten()
    sorted_observed = np.sort(observed)
    sorted_modeled = np.sort(modeled)
    corrected = np.interp(modeled, sorted_modeled, sorted_observed)
    corrected = pd.DataFrame(corrected, index=idx, columns=["corrected"])
    return corrected
# ================================================================================================ quantile mapping
def delta_change(observed, modeled):
    idx = observed.index
    observed = observed.to_numpy().flatten()
    modeled = modeled.to_numpy().flatten()
    change_factor = observed[-1] - observed[0]
    corrected = modeled + change_factor
    corrected = pd.DataFrame(corrected, index=idx, columns=["corrected"])
    return corrected
# ==================================================================================================== delta change
def empirical_quantile(observed, modeled):
    idx = observed.index
    observed = observed.to_numpy().flatten()
    modeled = modeled.to_numpy().flatten()
    percentiles = np.percentile(modeled, np.linspace(0, 100, len(observed)))
    corrected = np.interp(modeled, percentiles, observed)
    corrected = pd.DataFrame(corrected, index=idx, columns=["corrected"])
    return corrected
# ============================================================================================== empirical quantile
def variance_scaling(observed, modeled):
    mean_factor = np.mean(observed) / np.mean(modeled)
    std_factor = np.std(observed) / np.std(modeled)
    corrected = (modeled - np.mean(modeled)) * std_factor + np.mean(observed)
    return corrected
# ================================================================================================ variance scaling
#
#
def kge_calculate(observed, modeled):
    # Ensure inputs are NumPy arrays
    modeled = np.asarray(modeled)
    observed = np.asarray(observed)
    # Remove NaN values
    mask = ~np.isnan(modeled) & ~np.isnan(observed)
    modeled = modeled[mask]
    observed = observed[mask]
    # Calculate correlation coefficient (r)
    r = np.corrcoef(modeled, observed)[0, 1]
    # Calculate standard deviation ratio (alpha)
    alpha = np.std(modeled) / np.std(observed)
    # Calculate mean ratio (beta)
    beta = np.mean(modeled) / np.mean(observed)
    # Compute KGE score
    kge_value = 1 - np.sqrt((r - 1)**2 + (alpha - 1)**2 + (beta - 1)**2)
    return kge_value

def calculate_metrics(observed_data, modeled_data, reference_data=None):
    print(f"Calculating metrics for: {modeled_data.columns}") # Check columns
    # Make sure to select the correct columns if needed
    obs_col = observed_data.columns[-1] # Assume last column is value
    mod_col = modeled_data.columns[-1] # Assume last column is value

    # Ensure series have same index for comparison
    common_index = observed_data.index.intersection(modeled_data.index)
    if common_index.empty:
        print("Warning: No common index found between observed and modeled data.")
        return {'RMSE': float('nan'), 'MAE': float('nan'), 'Bias': float('nan'), 'Correlation': float('nan'), 'NSE': float('nan'), 'KGE': float('nan')}

    obs = observed_data.loc[common_index, obs_col].astype(float)
    mod = modeled_data.loc[common_index, mod_col].astype(float)
    # Basic example calculations (replace with proper library like hydroeval or sklearn)
    diff = mod - obs
    rmse = (diff**2).mean()**0.5
    mae = diff.abs().mean()
    bias = diff.mean()
    corr = obs.corr(mod) # Pandas correlation
    nse = 1 - ((diff**2).sum() / ((obs - obs.mean())**2).sum())
    kge = kge_calculate(obs, mod)

    return {
        'RMSE': rmse if pd.notna(rmse) else float('nan'),
        'MAE': mae if pd.notna(mae) else float('nan'),
        'Bias': bias if pd.notna(bias) else float('nan'),
        'Correlation': corr if pd.notna(corr) else float('nan'),
        'NSE': nse if pd.notna(nse) else float('nan'),
        'KGE': kge if pd.notna(kge) else float('nan'),
    }

def generate_plot(observed_data, corrected_data, remote_data):
    """
    Generate an interactive Plotly chart (as an embeddable HTML fragment) comparing
    observed, original remote, and bias-corrected series. Zoom (scroll/box-select)
    and pan are Plotly defaults.
    """
    try:
        obs_col = observed_data.columns[-1]
        rem_col = remote_data.columns[-1]
        cor_col = corrected_data.columns[-1]

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=observed_data.index, y=observed_data[obs_col],
            mode='lines', name='Observed',
            line=dict(color='#1d3557'),
        ))
        fig.add_trace(go.Scatter(
            x=remote_data.index, y=remote_data[rem_col],
            mode='lines', name='Original Remote',
            line=dict(color='#e63946', dash='dash'),
        ))
        fig.add_trace(go.Scatter(
            x=corrected_data.index, y=corrected_data[cor_col],
            mode='lines', name='Corrected',
            line=dict(color='#1abc9c'),
        ))

        fig.update_layout(
            title='Bias Correction Comparison',
            xaxis_title='Date',
            yaxis_title='Value',
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
        logger.exception("Error generating bias correction plot")
        return None

# =================================================================================================================


# CREATE VIEWS HERE.
# _____________________________________________________________________________________________________________BIAS_VIEW____
@login_required
def bias(request):
    context = {}

    if request.user.is_authenticated:
        template_name = 'base_usr.html'
    else:
        template_name = 'base_all.html'

    context['template_name'] = template_name

    if request.method == 'POST':
        # Fetch files using the 'name' attributes from the HTML form
        observations_file = request.FILES.get('observations_file')
        remote_sensing_file = request.FILES.get('remote_sensing_file')

        # Fetch other form data using 'name' attributes
        variable_to_correct = request.POST.get('variable_select')
        # *** Use the correct key for the hidden input ***
        correction_method = request.POST.get('correction_method')

        # Basic validation
        if not all([observations_file, remote_sensing_file, variable_to_correct, correction_method]):
            messages.error(request, "Missing required form fields or files. Please ensure all fields are filled and files are selected.")
            return render(request, 'tools/bias_correction.html', context)

        # Process files dynamically based on extension
        def read_file(file):
            try:
                if file.name.endswith('.csv'):
                    return pd.read_csv(file, parse_dates=True, index_col=0)
                elif file.name.endswith(('.xlsx', '.xls')):
                    return pd.read_excel(file, parse_dates=True, index_col=0)
                else:
                    raise ValueError("Unsupported file format.")
            except Exception as e:
                raise ValueError(f"Error reading file '{file.name}': {e}. Ensure format is correct and first column is a parsable date.")

        try:
            observed_data = read_file(observations_file)
            remote_data = read_file(remote_sensing_file)
            corrected_data = None
            # Apply selected correction method
            if correction_method == "linear_scaling":
                correction_method_name = "Linear Scaling"
                corrected_data = linear_scaling(observed_data, remote_data)
            elif correction_method == "quantile_mapping":
                correction_method_name = "Quantile Mapping"
                corrected_data = quantile_mapping(observed_data, remote_data)
            elif correction_method == "delta_change":
                correction_method_name = "Delta Change"
                corrected_data = delta_change(observed_data, remote_data)
            elif correction_method == "empirical_quantile":
                correction_method_name = "Empirical Quantile"
                corrected_data = empirical_quantile(observed_data, remote_data)
            elif correction_method == "variance_scaling":
                correction_method_name = "Variance Scaling"
                corrected_data = variance_scaling(observed_data, remote_data)
            else:
                 messages.error(request, f"Unknown correction method selected: {correction_method}")
                 return render(request, 'tools/bias_correction.html', context)

            if corrected_data is None or corrected_data.empty:
                 messages.error(request, f"Bias correction method '{correction_method}' failed to produce results.")
                 return render(request, 'tools/bias_correction.html', context)

            # Generate Plot
            plot_data_html = generate_plot(observed_data, corrected_data, remote_data)
            if plot_data_html:
                 context['plot_html'] = plot_data_html
            else:
                 messages.warning(request, "Could not generate the results plot.")

            # Calculate Metrics (Add error handling)
            try:
                 # Calculate metrics ONLY if corrected_data is valid
                 metrics_before = calculate_metrics(observed_data, remote_data)
                 metrics_after = calculate_metrics(observed_data, corrected_data)
                 context['metrics_before'] = metrics_before
                 context['metrics_after'] = metrics_after
                 context['corrected_csv'] = corrected_data.to_csv()
                 context['correction_method_name'] = correction_method_name
                 context['metrics_json'] = json.dumps({
                     'before': _serializable_metrics(metrics_before),
                     'after': _serializable_metrics(metrics_after),
                 })

                 # --- Calculate Percentage Differences ---
                 def calculate_percentage_diff(before, after):
                    if before is not None and after is not None and before != 0:
                        try:
                            diff = after - before
                            return (diff / abs(before)) * 100
                        except (TypeError, ZeroDivisionError):
                            return None
                    return None

                 context['rmse_percentage_diff'] = calculate_percentage_diff(metrics_before.get('RMSE'), metrics_after.get('RMSE'))
                 context['mae_percentage_diff'] = calculate_percentage_diff(metrics_before.get('MAE'), metrics_after.get('MAE'))
                 context['bias_percentage_diff'] = calculate_percentage_diff(metrics_before.get('Bias'), metrics_after.get('Bias'))
                 context['correlation_percentage_diff'] = calculate_percentage_diff(metrics_before.get('Correlation'), metrics_after.get('Correlation'))
                 context['nse_percentage_diff'] = calculate_percentage_diff(metrics_before.get('NSE'), metrics_after.get('NSE'))
                 context['kge_percentage_diff'] = calculate_percentage_diff(metrics_before.get('KGE'), metrics_after.get('KGE'))

                 messages.success(request, f"{correction_method_name} Bias Correction Processed Successfully!") # Success message
            except Exception as e:
                 logger.exception("Bias correction: error calculating metrics")
                 messages.error(request, "Error calculating metrics from the provided data.")

        except ValueError as e:
            messages.error(request, f"Error processing files: {e}")
        except Exception as e:
            logger.exception("Bias correction: unexpected processing error")
            messages.error(request, "An unexpected processing error occurred. Please check your data or contact support.")

        return render(request, 'tools/bias_correction.html', context)

    return render(request, 'tools/bias_correction.html', context)


def _serializable_metrics(metrics):
    """Convert numpy scalar metric values to plain JSON-safe floats."""
    result = {}
    for key, value in metrics.items():
        try:
            result[key] = float(value)
        except (TypeError, ValueError):
            result[key] = None
    return result


# ________________________________________________________________________________________________________EXPORT_VIEWS____
@login_required
def bias_export_csv(request):
    """Download the corrected-data table produced by the last bias correction run."""
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    csv_data = request.POST.get('corrected_csv', '')
    response = HttpResponse(csv_data, content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="bias_corrected_data.csv"'
    return response


@login_required
def bias_export_pdf(request):
    """Generate a PDF summary (method + before/after metrics) of the last bias correction run."""
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    method_name = request.POST.get('correction_method_name', 'Bias Correction')
    try:
        metrics = json.loads(request.POST.get('metrics_json', '{}'))
    except (json.JSONDecodeError, TypeError):
        metrics = {}
    before = metrics.get('before', {})
    after = metrics.get('after', {})

    buffer = BytesIO()
    pdf = pdf_canvas.Canvas(buffer)

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(72, 780, "Bias Correction Report")
    pdf.setFont("Helvetica", 11)
    pdf.drawString(72, 758, f"Method: {method_name}")

    y = 720
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(72, y, "Metric")
    pdf.drawString(220, y, "Before")
    pdf.drawString(320, y, "After")
    y -= 8
    pdf.line(72, y, 400, y)
    y -= 18

    pdf.setFont("Helvetica", 11)
    for key in ['RMSE', 'MAE', 'Bias', 'Correlation', 'NSE', 'KGE']:
        b = before.get(key)
        a = after.get(key)
        pdf.drawString(72, y, key)
        pdf.drawString(220, y, f"{b:.3f}" if isinstance(b, (int, float)) else "-")
        pdf.drawString(320, y, f"{a:.3f}" if isinstance(a, (int, float)) else "-")
        y -= 20

    pdf.save()
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="bias_correction_report.pdf"'
    return response
