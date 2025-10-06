from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers
import pickle
import numpy as np
import pandas as pd


# Serializer for input data
class ForecastRequestSerializer(serializers.Serializer):
    start_year = serializers.IntegerField()
    start_month = serializers.IntegerField()
    start_day = serializers.IntegerField()
    end_year = serializers.IntegerField()
    end_month = serializers.IntegerField()
    end_day = serializers.IntegerField()

# Load the trained model outputs and training data
model_path = "models/output.pkl"
with open(model_path, 'rb') as f:
    model_output = pickle.load(f)

excel_path = "data/water_levels_data.xlsx"
try:
    training_data = pd.read_excel(excel_path)
    training_data = training_data.sort_values('Date')
    cont_columns = training_data.columns.drop(['Date', 'Lake_Level'])
    training_data[cont_columns] = np.log(training_data[cont_columns])
    # training_data = training_data.drop(columns=['Discharge_Depth','Streamflow_Depth','Evaporation','Precipitation'])
    training_data = training_data.dropna()
except Exception as e:
    training_data = None
    print(f"Error loading training data: {e}")

def forecast(start, end, training_data, horizon=120):
    if training_data is None:
        raise ValueError("Training data is not loaded.")
    start_date = pd.Timestamp(year=start['year'], month=start['month'], day=start['day'])
    end_date = pd.Timestamp(year=end['year'], month=end['month'], day=end['day'])
    assert end_date > start_date, "End Date should be greater than Start Date"

    training_data = training_data.sort_values('Date')
    max_date_train = training_data['Date'].max()
    if end_date <= max_date_train:
        sample = training_data[(training_data['Date'] >= start_date) & (training_data['Date'] <= end_date)]
        return sample.to_dict(orient="records")

    models = model_output['models']
    weights = model_output['weights']
    features = model_output['features']
    if start_date < max_date_train:
        results = []
        sample = training_data[(training_data['Date'] >= start_date) & (training_data['Date'] <= max_date_train)]
        results.extend(sample.to_dict(orient="records"))
        future_timestamps = pd.date_range(start=max_date_train + pd.Timedelta(days=1), end=end_date, freq='D')
        df_future = pd.DataFrame({'Date':future_timestamps})
        df_future['split'] = 'future'
        training_data['split'] = 'train'
        combined = pd.concat([training_data, df_future])
        combined['month'] = combined['Date'].dt.month
        combined['dayofweek'] = combined['Date'].dt.dayofweek
        combined['year'] = combined['Date'].dt.year
        year_min= training_data['Date'].dt.year.min()
        combined['years_since_min'] = combined['year'] - year_min
        combined['day'] = combined['Date'].dt.day
        combined['weekend'] = (combined['dayofweek'] >= 5).astype('int32')
        combined['quarter'] = combined['Date'].dt.quarter
        combined['week'] = combined['Date'].dt.isocalendar().week
        combined = combined.drop(['year'], axis=1)
        combined = pd.get_dummies(data=combined, columns=['dayofweek', 'month', 'quarter', 'week'], dtype='int32')
        combined = combined.sort_values('Date')
        combined['lag_Lake_Level'] = combined['Lake_Level'].shift(horizon).bfill()
        future_dataset = combined[combined['split'] == 'future'].drop(['split'], axis=1).reset_index(drop=True)
        model_predictions = []
        for model in models:
            X = future_dataset[:horizon].drop(['Date', 'Lake_Level'], axis=1)[features]
            y_hat = np.exp(model.predict(X))
            model_predictions.append(y_hat)
        y_hat = np.sum(np.array(model_predictions) * weights[:, np.newaxis], axis=0)
        future_dataset.loc[:horizon-1, 'Lake_Level'] = y_hat
        predictions = []
        lag_Lake_Level = y_hat[-1]
        for _, row in future_dataset[horizon:].iterrows():
            row['lag_Lake_Level'] = lag_Lake_Level
            model_predictions = []
            for model in models:
                X = row.drop(['Date', 'Lake_Level'])[features].to_frame().T.astype('float32')
                y_hat = np.exp(model.predict(X))
                model_predictions.append(y_hat)
            y_hat = np.sum(np.array(model_predictions) * weights[:, np.newaxis], axis=0)
            lag_Lake_Level = y_hat
            predictions.append(y_hat)
        future_dataset.loc[horizon:, 'Lake_Level'] = predictions
        sample = future_dataset[['Date', 'Lake_Level']]
        results.extend(sample.to_dict(orient="records"))
        return results
    if start_date > max_date_train:
        results = []
        future_timestamps = pd.date_range(start=max_date_train + pd.Timedelta(days=1), end=end_date, freq='D')
        df_future = pd.DataFrame({'Date':future_timestamps})
        df_future['split'] = 'future'
        training_data['split'] = 'train'
        combined = pd.concat([training_data, df_future])
        combined['month'] = combined['Date'].dt.month
        combined['dayofweek'] = combined['Date'].dt.dayofweek
        combined['year'] = combined['Date'].dt.year
        year_min= training_data['Date'].dt.year.min()
        combined['years_since_min'] = combined['year'] - year_min
        combined['day'] = combined['Date'].dt.day
        combined['weekend'] = (combined['dayofweek'] >= 5).astype('int32')
        combined['quarter'] = combined['Date'].dt.quarter
        combined['week'] = combined['Date'].dt.isocalendar().week
        combined = combined.drop(['year'], axis=1)
        combined = pd.get_dummies(data=combined, columns=['dayofweek', 'month', 'quarter', 'week'], dtype='int32')
        combined = combined.sort_values('Date')
        combined['lag_Lake_Level'] = combined['Lake_Level'].shift(horizon).bfill()
        future_dataset = combined[combined['split'] == 'future'].drop(['split'], axis=1).reset_index(drop=True)
        model_predictions = []
        for model in models:
            X = future_dataset[:horizon].drop(['Date', 'Lake_Level'], axis=1)[features]
            y_hat = np.exp(model.predict(X))
            model_predictions.append(y_hat)
        y_hat = np.sum(np.array(model_predictions) * weights[:, np.newaxis], axis=0)
        future_dataset.loc[:horizon-1, 'Lake_Level'] = y_hat
        predictions = []
        lag_Lake_Level = y_hat[-1]
        for _, row in future_dataset[horizon:].iterrows():
            row['lag_Lake_Level'] = lag_Lake_Level
            model_predictions = []
            for model in models:
                X = row.drop(['Date', 'Lake_Level'])[features].to_frame().T.astype('float32')
                y_hat = np.exp(model.predict(X))
                model_predictions.append(y_hat)
            y_hat = np.sum(np.array(model_predictions) * weights[:, np.newaxis], axis=0)
            lag_Lake_Level = y_hat
            predictions.append(y_hat)
        future_dataset.loc[horizon:, 'Lake_Level'] = predictions
        future_dataset = future_dataset[future_dataset['Date'] >= start_date]
        sample = future_dataset[['Date', 'Lake_Level']]
        results.extend(sample.to_dict(orient="records"))
        return results

class ForecastLakeLevelsView(APIView):
    def post(self, request):
        serializer = ForecastRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        if training_data is None:
            return Response({"error": "Training data not loaded."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        validated_data = serializer.validated_data
        required_keys = ['start_year', 'start_month', 'start_day', 'end_year', 'end_month', 'end_day']
        if not isinstance(validated_data, dict) or not all(k in validated_data for k in required_keys):
            return Response({"error": "Invalid or empty input data."}, status=status.HTTP_400_BAD_REQUEST)
        start = {
            "year": validated_data['start_year'],
            "month": validated_data['start_month'],
            "day": validated_data['start_day']
        }
        end = {
            "year": validated_data['end_year'],
            "month": validated_data['end_month'],
            "day": validated_data['end_day']
        }
        try:
            results = forecast(start, end, training_data)
            if results is None:
                return Response({"error": "No forecast results returned."}, status=status.HTTP_404_NOT_FOUND)
            # Convert numpy types to native Python types for JSON serialization
            for r in results:
                r["Date"] = r["Date"].strftime("%Y-%m-%d") if hasattr(r["Date"], "strftime") else str(r["Date"])
                if "Lake_Level" in r and hasattr(r["Lake_Level"], "item"):
                    r["Lake_Level"] = r["Lake_Level"].item()
            return Response({"forecast": results}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class HealthCheckView(APIView):
    def get(self, request):
        return Response({"status": "healthy", "model": "lake_level_forecast_v1"}, status=status.HTTP_200_OK)