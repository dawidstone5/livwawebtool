import pandas as pd, numpy as np
from django.shortcuts import render
from django.contrib import messages
import base64
from io import BytesIO
import matplotlib.pyplot as plt

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
    print("Generating plot...")
    try:
        fig, ax = plt.subplots(figsize=(10, 5))
        # Assuming dataframes have a datetime index or a 'Date' column
        # Adjust column selection as needed
        obs_col = observed_data.columns[-1]
        rem_col = remote_data.columns[-1]
        cor_col = corrected_data.columns[-1]

        ax.plot(observed_data.index, observed_data[obs_col], label='Observed', color='#1d3557', alpha=0.8)
        ax.plot(remote_data.index, remote_data[rem_col], label='Original Remote', color='#e63946', linestyle='--', alpha=0.7)
        ax.plot(corrected_data.index, corrected_data[cor_col], label='Corrected', color='#1abc9c')

        ax.set_xlabel("Date")
        ax.set_ylabel("Value")
        ax.set_title("Bias Correction Comparison")
        ax.legend()
        ax.grid(True, linestyle=':', alpha=0.6)
        plt.tight_layout()

        # Save plot to a bytes buffer
        buf = BytesIO()
        plt.savefig(buf, format='png')
        plt.close(fig) # Close the figure to free memory
        buf.seek(0)

        # Encode bytes to base64 string
        plot_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        return plot_base64
    except Exception as e:
        print(f"Error generating plot: {e}")
        return None

# =================================================================================================================


# CREATE VIEWS HERE.
# _____________________________________________________________________________________________________________BIAS_VIEW____
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
            plot_data_base64 = generate_plot(observed_data, corrected_data, remote_data)
            if plot_data_base64:
                 context['plot_base64'] = plot_data_base64
            else:
                 messages.warning(request, "Could not generate the results plot.")

            # Calculate Metrics (Add error handling)
            try:
                 # Calculate metrics ONLY if corrected_data is valid
                 metrics_before = calculate_metrics(observed_data, remote_data)
                 metrics_after = calculate_metrics(observed_data, corrected_data)
                 context['metrics_before'] = metrics_before
                 context['metrics_after'] = metrics_after
                 
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
                 messages.error(request, f"Error calculating metrics: {e}")

        except ValueError as e:
            messages.error(request, f"Error processing files: {e}")
        except Exception as e:
            messages.error(request, f"An unexpected processing error occurred. Please check your data or contact support. Error: {e}")

        return render(request, 'tools/bias_correction.html', context)

    return render(request, 'tools/bias_correction.html', context)
