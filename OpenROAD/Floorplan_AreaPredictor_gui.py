import joblib
import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk

class AreaPredictionInterface:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Circuit Area Predictor")
        self.root.geometry("600x800")
        self.model = None
        self.setup_ui()

    def setup_ui(self):
        # Create main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Load Model Button
        ttk.Button(main_frame, text="Load Trained Model", 
                  command=self.load_model).grid(row=0, column=0, pady=10)

        # Feature input fields
        self.feature_entries = {}
        self.feature_vars = {}
        
        features = [
            ('total_cell_count', 'Total Cell Count', '1234'),
            ('sequential_cells', 'Sequential Cells', '567'),
            ('combinational_cells', 'Combinational Cells', '667'),
            ('macro_count', 'Macro Count', '2'),
            ('total_instances', 'Total Instances', '1236'),
            ('memory_bits', 'Memory Bits', '8192'),
            ('memory_instances', 'Memory Instances', '1'),
            ('total_nets', 'Total Nets', '2345'),
            ('total_pins', 'Total Pins', '4567'),
            ('avg_fanout', 'Average Fanout', '3.7'),
            ('utilization', 'Utilization', '0.7')
        ]

        for idx, (key, label, default) in enumerate(features):
            ttk.Label(main_frame, text=label).grid(row=idx+1, column=0, pady=2)
            self.feature_vars[key] = tk.StringVar(value=default)
            entry = ttk.Entry(main_frame, textvariable=self.feature_vars[key])
            entry.grid(row=idx+1, column=1, pady=2)
            self.feature_entries[key] = entry

        # Predict Button
        ttk.Button(main_frame, text="Predict Area", 
                  command=self.predict_area).grid(row=len(features)+1, column=0, 
                                                columnspan=2, pady=20)

        # Results Display
        self.result_text = tk.Text(main_frame, height=10, width=60)
        self.result_text.grid(row=len(features)+2, column=0, columnspan=2, pady=10)

    def load_model(self):
        try:
            model_path = filedialog.askopenfilename(
                title="Select Trained Model File",
                filetypes=[("Joblib files", "*.joblib")]
            )
            if model_path:
                self.model = joblib.load(model_path)
                self.result_text.insert(tk.END, f"Model loaded successfully from: {model_path}\n")
                messagebox.showinfo("Success", "Model loaded successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Error loading model: {str(e)}")

    def get_feature_values(self):
        features = {}
        for key, entry in self.feature_entries.items():
            try:
                value = float(self.feature_vars[key].get())
                features[key] = value
            except ValueError:
                raise ValueError(f"Invalid value for {key}. Please enter a number.")
        return features

    def predict_area(self):
        if self.model is None:
            messagebox.showerror("Error", "Please load a trained model first!")
            return

        try:
            # Get feature values
            features = self.get_feature_values()
            
            # Prepare input features
            X = np.array([[
                features['total_cell_count'],
                features['sequential_cells'],
                features['combinational_cells'],
                features['macro_count'],
                features['total_instances'],
                features['memory_bits'],
                features['memory_instances'],
                features['total_nets'],
                features['total_pins'],
                features['avg_fanout'],
                features['utilization']
            ]])

            # Scale features
            X_scaled = self.model['scaler'].transform(X)
            
            # Make predictions
            die_corners = self.model['model_die'].predict(X_scaled)[0]
            core_corners = self.model['model_core'].predict(X_scaled)[0]

            # Display results
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, "Prediction Results:\n\n")
            self.result_text.insert(tk.END, 
                f"set die_area {{{die_corners[0]:.2f} {die_corners[1]:.2f} "
                f"{die_corners[2]:.2f} {die_corners[3]:.2f}}}\n")
            self.result_text.insert(tk.END, 
                f"set core_area {{{core_corners[0]:.2f} {core_corners[1]:.2f} "
                f"{core_corners[2]:.2f} {core_corners[3]:.2f}}}\n")

            # Calculate and display areas
            die_area = (die_corners[2] - die_corners[0]) * (die_corners[3] - die_corners[1])
            core_area = (core_corners[2] - core_corners[0]) * (core_corners[3] - core_corners[1])
            
            self.result_text.insert(tk.END, f"\nDie Area: {die_area:.2f} square units")
            self.result_text.insert(tk.END, f"\nCore Area: {core_area:.2f} square units")
            self.result_text.insert(tk.END, f"\nCore/Die Ratio: {(core_area/die_area)*100:.1f}%")

        except Exception as e:
            messagebox.showerror("Error", f"Error making prediction: {str(e)}")

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = AreaPredictionInterface()
    app.run()
