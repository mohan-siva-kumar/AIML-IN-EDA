import os
import subprocess
import re
import json
import tempfile

class MultiDesignFeatureExtractor:
    def __init__(self):
        self.all_features = {}
        self.feature_template = {
            'design_name': '',
            'gate_count': 0,
            'total_wire_length': 0,
            'memory_bits': 0,
            'standard_cells_count': 0,
            'macro_count': 0,
            'metal_layers': 0,
            'power_domains': 1,
            'voltage_domains': 1,
            'io_pad_count': 0,
            'chip_area': 0.0,
            'combinational_area': 0.0,
            'noncombinational_area': 0.0,
            'buf_inv_area': 0.0,
            'total_cell_area': 0.0
        }

    def get_initial_inputs(self):
        """Get number of designs and common files"""
        print("\n=== Initial Setup ===")
        while True:
            try:
                num_designs = int(input("Enter number of Verilog designs to process: "))
                if num_designs > 0:
                    break
                print("Please enter a positive number.")
            except ValueError:
                print("Please enter a valid number.")

        print("\n=== Enter Common File Paths ===")
        liberty_file = input("Enter path to Liberty file (.lib): ").strip()
        lef_file = input("Enter path to LEF file (.lef): ").strip()

        # Validate common files exist
        for file_path in [liberty_file, lef_file]:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")

        return num_designs, liberty_file, lef_file

    def get_design_inputs(self, design_number):
        """Get inputs for a specific design"""
        print(f"\n=== Design {design_number} Details ===")
        while True:
            verilog_file = input(f"Enter path to Verilog file {design_number} (.v): ").strip()
            if os.path.exists(verilog_file):
                break
            print("File not found. Please enter a valid path.")

        while True:
            top_module = input(f"Enter top module name for design {design_number}: ").strip()
            if top_module:
                break
            print("Top module name cannot be empty.")

        # Extract design name from file path
        design_name = os.path.splitext(os.path.basename(verilog_file))[0]
        return verilog_file, top_module, design_name

    def run_yosys_analysis(self, verilog_file, liberty_file, top_module, design_name):
        """Run Yosys synthesis with specified commands"""
        print(f"\nProcessing Design: {design_name}")
        
        # Create output directory for this design
        design_output_dir = f"output/{design_name}"
        os.makedirs(design_output_dir, exist_ok=True)

        # Create Yosys script
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ys', delete=False) as tmp:
            yosys_script = f"""
            # Read Liberty file
            read_liberty -lib -ignore_miss_dir -setattr blackbox "{liberty_file}"

            # Read design
            read_verilog {verilog_file}

            # Set and check hierarchy
            hierarchy -check -top {top_module}

            # High-level synthesis
            proc
            fsm
            opt
            memory
            opt

            # Technology mapping
            techmap
            opt
            dfflibmap -liberty {liberty_file}
            opt
            abc -liberty {liberty_file}

            # Cleanup and finalization
            flatten
            setundef -zero
            clean -purge
            
            # Map I/O pads
            iopadmap -outpad BUF_X2 A:Z -bits
            opt
            clean

            # Get statistics
            stat -liberty {liberty_file}

            # Rename and write outputs
            rename -enumerate
            write_verilog -noattr {design_output_dir}/{top_module}_netlist.v
            write_blif -buf BUF_X2 A Z {design_output_dir}/{top_module}_mapped_withbuf.blif

            # Show design
            show -stretch -prefix {design_output_dir}/{top_module}_diagram
            """
            tmp.write(yosys_script)
            script_path = tmp.name

        try:
            # Run Yosys
            result = subprocess.run(['yosys', script_path], 
                                 capture_output=True, 
                                 text=True,
                                 check=True)
            
            # Parse Yosys output
            output = result.stdout
            
            # Initialize features for this design
            self.all_features[design_name] = self.feature_template.copy()
            self.all_features[design_name]['design_name'] = design_name
            
            # Extract basic features
            gate_match = re.search(r'Number of cells:\s+(\d+)', output)
            wire_match = re.search(r'Number of wires:\s+(\d+)', output)
            mem_match = re.search(r'Memory bits:\s+(\d+)', output)

            if gate_match:
                self.all_features[design_name]['gate_count'] = int(gate_match.group(1))
            if wire_match:
                self.all_features[design_name]['total_wire_length'] = int(wire_match.group(1))
            if mem_match:
                self.all_features[design_name]['memory_bits'] = int(mem_match.group(1))

            # Extract area information
            chip_area_match = re.search(r'Chip area for top module.*?:\s*([\d.]+)', output)
            comb_area_match = re.search(r'Combinational area:\s*([\d.]+)', output)
            noncomb_area_match = re.search(r'Noncombinational area:\s*([\d.]+)', output)
            buf_inv_match = re.search(r'Buf/Inv area:\s*([\d.]+)', output)
            total_area_match = re.search(r'Total cell area:\s*([\d.]+)', output)

            if chip_area_match:
                self.all_features[design_name]['chip_area'] = float(chip_area_match.group(1))
            if comb_area_match:
                self.all_features[design_name]['combinational_area'] = float(comb_area_match.group(1))
            if noncomb_area_match:
                self.all_features[design_name]['noncombinational_area'] = float(noncomb_area_match.group(1))
            if buf_inv_match:
                self.all_features[design_name]['buf_inv_area'] = float(buf_inv_match.group(1))
            if total_area_match:
                self.all_features[design_name]['total_cell_area'] = float(total_area_match.group(1))

            # Save Yosys log
            with open(f'{design_output_dir}/yosys_log.txt', 'w') as f:
                f.write(output)

            print(f"\nFeatures extracted for {design_name}:")
            print(f"  Gate Count: {self.all_features[design_name]['gate_count']}")
            print(f"  Wire Length: {self.all_features[design_name]['total_wire_length']}")
            print(f"  Memory Bits: {self.all_features[design_name]['memory_bits']}")
            print(f"  Chip Area: {self.all_features[design_name]['chip_area']}")
            print(f"  Total Cell Area: {self.all_features[design_name]['total_cell_area']}")
            
        except subprocess.CalledProcessError as e:
            print(f"Error running Yosys for {design_name}: {e}")
            print(f"Yosys stderr: {e.stderr}")
            raise
        finally:
            os.unlink(script_path)

    def extract_lef_features(self, lef_file):
        """Extract features from LEF file"""
        print("\nProcessing LEF file...")
        
        try:
            with open(lef_file, 'r') as f:
                content = f.read()
            
            # Extract features
            std_cells = re.findall(r'MACRO\s+\w+_\d+X\d+', content)
            all_macros = re.findall(r'MACRO\s+(\w+)', content)
            metal_layers = re.findall(r'LAYER\s+metal\d+', content)

            # Add LEF features to all designs
            for design_name in self.all_features:
                self.all_features[design_name]['standard_cells_count'] = len(std_cells)
                self.all_features[design_name]['macro_count'] = len(all_macros) - len(std_cells)
                self.all_features[design_name]['metal_layers'] = len(metal_layers)

            print("LEF features extracted and applied to all designs:")
            print(f"  Standard Cells: {len(std_cells)}")
            print(f"  Macros: {len(all_macros) - len(std_cells)}")
            print(f"  Metal Layers: {len(metal_layers)}")
            
        except Exception as e:
            print(f"Error processing LEF file: {e}")
            raise

    def extract_lib_features(self, lib_file):
        """Extract features from Liberty file"""
        print("\nProcessing Liberty file...")
        
        try:
            with open(lib_file, 'r') as f:
                content = f.read()
            
            # Extract features
            io_pads = re.findall(r'cell\s*\(\s*\w*pad\w*\s*\)', content)
            power_match = re.search(r'power_domains\s*:\s*(\d+)', content)
            voltage_match = re.search(r'voltage_domains\s*:\s*(\d+)', content)

            # Add Liberty features to all designs
            for design_name in self.all_features:
                self.all_features[design_name]['io_pad_count'] = len(io_pads)
                if power_match:
                    self.all_features[design_name]['power_domains'] = int(power_match.group(1))
                if voltage_match:
                    self.all_features[design_name]['voltage_domains'] = int(voltage_match.group(1))

            print("Liberty features extracted and applied to all designs:")
            print(f"  I/O Pads: {len(io_pads)}")
            print(f"  Power Domains: {1 if not power_match else int(power_match.group(1))}")
            print(f"  Voltage Domains: {1 if not voltage_match else int(voltage_match.group(1))}")
            
        except Exception as e:
            print(f"Error processing Liberty file: {e}")
            raise

def main():
    extractor = MultiDesignFeatureExtractor()
    
    try:
        # Create main output directory
        os.makedirs("output", exist_ok=True)

        # Get initial inputs
        num_designs, liberty_file, lef_file = extractor.get_initial_inputs()
        
        # Process each design
        for i in range(1, num_designs + 1):
            verilog_file, top_module, design_name = extractor.get_design_inputs(i)
            extractor.run_yosys_analysis(verilog_file, liberty_file, top_module, design_name)
        
        # Extract common features
        extractor.extract_lef_features(lef_file)
        extractor.extract_lib_features(liberty_file)
        
        # Save all features to JSON
        with open('output/all_design_features.json', 'w') as f:
            json.dump(extractor.all_features, f, indent=2)
        
        print("\nAll features extracted successfully!")
        print("Results saved in 'output' directory:")
        print("  - all_design_features.json: Combined features for all designs")
        print("  - [design_name]/: Separate directory for each design's outputs")
        
    except Exception as e:
        print(f"\nError during feature extraction: {e}")

if __name__ == "__main__":
    main()
