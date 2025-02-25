import pandas as pd
import numpy as np
import subprocess
import re
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
import joblib
import json
import os
import sys
from pathlib import Path

class CongestionModelTrainer:
    def __init__(self):
        self.model = None
        self.feature_columns = None
        self.target_column = 'congestion_risk_score'
    
    def load_dataset(self, dataset_path):
        """Load and prepare dataset from specified path"""
        try:
            df = pd.read_csv(dataset_path)
            print(f"\nDataset loaded successfully from {dataset_path}")
            print(f"Total samples: {len(df)}")
            return df
        except Exception as e:
            print(f"Error loading dataset: {e}")
            sys.exit(1)
    
    def prepare_features(self, df):
        """Prepare features for training"""
        # Exclude non-feature columns
        self.feature_columns = [col for col in df.columns if col not in 
                              [self.target_column, 'design_id', 'design_type', 'technology']]
        
        X = df[self.feature_columns]
        y = df[self.target_column]
        
        return X, y
    
    def train_model(self, X, y):
        """Train the congestion prediction model"""
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        self.model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.model.fit(X_train, y_train)
        
        y_pred = self.model.predict(X_test)
        mse = mean_squared_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        
        print("\nModel Training Results:")
        print(f"Mean Squared Error: {mse:.4f}")
        print(f"R² Score: {r2:.4f}")
        
        feature_importance = pd.DataFrame({
            'feature': self.feature_columns,
            'importance': self.model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        print("\nTop 5 Most Important Features:")
        print(feature_importance.head())
        
        return feature_importance
    
    def save_model(self, save_path):
        """Save trained model and feature information"""
        if not self.model:
            print("Error: No trained model to save")
            return
        
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        model_info = {
            'model': self.model,
            'feature_columns': self.feature_columns
        }
        joblib.dump(model_info, save_path)
        print(f"\nModel saved successfully to {save_path}")

class OpenRoadCongestionAnalyzer:
    def __init__(self, model_path):
        """Initialize the congestion analyzer with a trained model"""
        try:
            model_info = joblib.load(model_path)
            self.model = model_info['model']
            self.feature_columns = model_info['feature_columns']
            self.gcell_size = 15  # default GCell size in microns
            print(f"Model loaded successfully from {model_path}")
        except Exception as e:
            print(f"Error loading model: {e}")
            sys.exit(1)
    
    def get_user_input_features(self):
        """Get required features from user input"""
        print("\nEnter the following design features for congestion prediction:")
        features = {}
        for feature in self.feature_columns:
            if feature == 'die_area_um2':
                features[feature] = float(input(f"{feature} (um²): "))
            else:
                features[feature] = float(input(f"{feature}: "))
        return pd.DataFrame([features])

    def analyze_design(self):
        """Complete congestion analysis of the design"""
        features = self.get_user_input_features()
        congestion_predictions = self.predict_congestion(features)
        return self.generate_report(congestion_predictions)

    def predict_congestion(self, features):
        """Use trained model to predict congestion"""
        return self.model.predict(features)

    def generate_report(self, predictions):
        """Generate detailed congestion analysis report with suggestions"""
        report = {
            'overall_congestion_risk': float(predictions[0]),
            'suggestions': self.generate_suggestions(predictions[0])
        }
        return report

    def generate_suggestions(self, congestion_risk):
        """Generate specific suggestions for congestion mitigation"""
        suggestions = []
        
        if congestion_risk > 0.8:
            suggestions.append("Consider increasing cell spacing in congested regions.")
            suggestions.append("Optimize pin access and high-fanout nets.")
        if congestion_risk > 0.9:
            suggestions.append("Add routing tracks in congested metal layers.")
            suggestions.append("Redistribute logic to reduce routing demand.")
        
        return suggestions

def get_user_paths():
    """Get file paths from user input"""
    print("\nCongestion Analysis System Setup")
    print("================================")
    
    mode = input("\nSelect mode:\n1. Train new model\n2. Run analysis with existing model\nChoice (1/2): ")
    
    if mode == "1":
        dataset_path = input("\nEnter path to training dataset CSV file: ")
        while not os.path.exists(dataset_path):
            print("Error: File not found!")
            dataset_path = input("Enter path to training dataset CSV file: ")
        
        model_save_path = input("Enter path to save trained model (e.g., 'models/congestion_model.joblib'): ")
        
        return {
            'mode': 'train',
            'dataset_path': dataset_path,
            'model_save_path': model_save_path
        }
    
    elif mode == "2":
        model_path = input("\nEnter path to trained model file: ")
        while not os.path.exists(model_path):
            print("Error: Model file not found!")
            model_path = input("Enter path to trained model file: ")
        
        return {
            'mode': 'analyze',
            'model_path': model_path
        }
    
    else:
        print("Invalid choice!")
        sys.exit(1)

def main():
    paths = get_user_paths()
    
    if paths['mode'] == 'train':
        trainer = CongestionModelTrainer()
        print("\nLoading dataset...")
        df = trainer.load_dataset(paths['dataset_path'])
        print("\nPreparing features...")
        X, y = trainer.prepare_features(df)
        print("\nTraining model...")
        trainer.train_model(X, y)
        print("\nSaving model...")
        trainer.save_model(paths['model_save_path'])
        
    else:
        analyzer = OpenRoadCongestionAnalyzer(paths['model_path'])
        print("\nRunning congestion analysis...")
        report = analyzer.analyze_design()
        
        report_path = "congestion_analysis_report.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        
        print(f"\nAnalysis complete. Report saved to {report_path}")
        print("\nCongestion Analysis Summary:")
        print(f"Overall Congestion Risk: {report['overall_congestion_risk']:.2f}")
        print("\nSuggestions:")
        for suggestion in report['suggestions']:
            print(f"- {suggestion}")

if __name__ == "__main__":
    main()
