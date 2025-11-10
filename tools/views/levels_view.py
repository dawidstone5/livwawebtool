# import neccessary functions, libraries, and packages
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
import base64
from io import BytesIO
import matplotlib
matplotlib.use('Agg')  # Set backend before importing pyplot
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from tools.views.api_code import forecast, training_data


# function for plotting the results
def generate_plot(results_df, selected_variable):
    """
    Generate a base64 encoded plot from the results dataframe
    """
    try:
        # Ensure the variable data is in the correct format
        results_df[selected_variable] = results_df[selected_variable].apply(
            lambda x: x[0] if isinstance(x, (list, np.ndarray)) and len(x) > 0 else x
        )

        # Create the plot
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(
            results_df.index, 
            results_df[selected_variable], 
            label='Water Levels', 
            color='#1abc9c', 
            linewidth=2,
            alpha=0.8
        )
        
        # Styling
        ax.set_xlabel("Date", fontsize=12, fontweight='bold')
        ax.set_ylabel("Water Level (m)", fontsize=12, fontweight='bold')
        ax.set_title("Predicted Water Levels over Time", fontsize=14, fontweight='bold', pad=20)
        ax.legend(loc='best', frameon=True, shadow=True)
        ax.grid(True, linestyle=':', alpha=0.6, linewidth=0.5)
        
        # Rotate x-axis labels for better readability
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()

        # Convert plot to base64
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        plt.close(fig)
        buf.seek(0)
        plot_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        
        return plot_base64
    
    except Exception as e:
        print(f"Error generating plot: {e}")
        # Close any open figures to prevent memory leaks
        plt.close('all')
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
            plot_base64 = generate_plot(df, 'water_levels')
            
            if plot_base64:
                context.update({
                    "plot_base64": plot_base64,
                    "reference_start_date": start_date,
                    "reference_end_date": end_date,
                })
                messages.success(request, f"Water level prediction generated successfully for {start_date.strftime('%B %Y')} to {end_date.strftime('%B %Y')}.")
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