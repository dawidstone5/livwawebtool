# import neccessary functions, libraries, and packages
from django.shortcuts import render
import base64
from io import BytesIO
import matplotlib.pyplot as plt
import pandas as pd, numpy as np
from tools.views.api_code import forecast, training_data
from django.contrib.auth.decorators import login_required


# function for plotting the results
def generate_plot(results_df, selected_variable):
    try:
        results_df[selected_variable] = results_df[selected_variable].apply(
            lambda x: x[0] if isinstance(x, (list, np.ndarray)) and len(x) > 0 else x
        )

        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(results_df.index, results_df[selected_variable], label='Water Levels', color='#1abc9c', alpha=0.8)
        ax.set_xlabel("Date")
        ax.set_ylabel("Water Level (m)")
        ax.set_title("Predicted Water Levels over Time")
        ax.legend()
        ax.grid(True, linestyle=':', alpha=0.6)
        plt.tight_layout()

        buf = BytesIO()
        plt.savefig(buf, format='png')
        plt.close(fig)
        buf.seek(0)
        plot_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        return plot_base64
    except Exception as e:
        print(f"Error generating plot: {e}")
        return None


# levels view function to handle requests for water levels
@login_required
def levels(request):
    context = {}

    if request.user.is_authenticated:
        template_name = 'base_usr.html'
    else:
        template_name = 'base_all.html'

    context['template_name'] = template_name

    if request.method == 'POST':
        try:
            start_date = request.POST.get('reference_start', None)
            end_date = request.POST.get('reference_end', None)

            if not start_date or not end_date:
                context['error_message'] = "Missing start_date or end_date"
                return render(request, "tools/water_levels.html", context)
            start_date = pd.to_datetime(start_date)
            end_date = pd.to_datetime(end_date)
            start_date = start_date.replace(day=1)
            end_date = end_date.replace(day=1)

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

            results = forecast(start, end, training_data)
            if not results or len(results) == 0:
                context['error_message'] = "No forecast results returned."
                return render(request, "tools/water_levels.html", context)

            df = pd.DataFrame(results)

            # Ensure Date is datetime and set as index
            if 'Date' in df.columns:
                df['Date'] = pd.to_datetime(df['Date'])
                df.set_index('Date', inplace=True)

            # Use the correct column name for water level
            if 'Lake_Level' in df.columns:
                df.rename(columns={'Lake_Level': 'water_levels'}, inplace=True)
            elif 'water_levels' not in df.columns:
                context['error_message'] = "No water level data in forecast results."
                return render(request, "tools/water_levels.html", context)

            plot_base64 = generate_plot(df, 'water_levels')
            if plot_base64:
                context.update({
                    "plot_base64": plot_base64,
                    "reference_start_date": start_date,
                    "reference_end_date": end_date,
                })
            else:
                context['error_message'] = "Could not generate the results plot."

        except Exception as e:
            context['error_message'] = f"An error occurred: {str(e)}"

    return render(request, "tools/water_levels.html", context)
