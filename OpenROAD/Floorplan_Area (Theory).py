import subprocess
import re
import math

class YosysAreaCalculator:
    def __init__(self, liberty_path: str, design_path: str, top_module: str):
        self.liberty_path = liberty_path
        self.design_path = design_path
        self.top_module = top_module
        # PDN-specific constants
        self.metal4_min_width = 28.48  # minimum width needed for metal4 straps
        self.strap_offset = 2.0        # strap offset
        self.pdn_margin = 1.4         # safety margin for PDN routing

    def execute_yosys_commands(self) -> str:
        """Execute commands in Yosys and capture output."""
        commands = [
            f'read_liberty -lib -ignore_miss_dir -setattr blackbox "{self.liberty_path}"',
            f'read_verilog {self.design_path}',
            f'hierarchy -check -top {self.top_module}',
            'proc',
            'opt',
            'fsm',
            'opt',
            'memory',
            'opt',
            'techmap',
            'opt',
            f'dfflibmap -liberty {self.liberty_path}',
            'opt',
            f'abc -liberty {self.liberty_path}',
            'flatten',
            'setundef -zero',
            'clean -purge',
            'iopadmap -outpad BUF_X2 A:Z -bits',
            'opt',
            'clean',
            f'stat -liberty {self.liberty_path}',
            'rename -enumerate'
        ]

        process = subprocess.Popen(['yosys', '-Q'], 
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True)

        commands_str = '\n'.join(commands) + '\nexit\n'
        stdout, stderr = process.communicate(commands_str)

        if process.returncode != 0:
            raise Exception(f"Yosys execution failed:\n{stderr}")

        return stdout

    def extract_and_save_area(self, yosys_output: str) -> float:
        """Extract area and save to chip.txt."""
        pattern = r'Chip area for module.*?:\s*"?([\d.]+)"?'
        area_match = re.search(pattern, yosys_output)
        
        if area_match:
            area = float(area_match.group(1))
            # Add PDN overhead to the area
            area = area * self.pdn_margin
            with open('chip.txt', 'w') as f:
                f.write(str(area))
            print(f"Area value {area} (including PDN margin) has been saved to chip.txt")
            return area
        else:
            print("Error: Could not extract area from Yosys output")
            return None

    def calculate_corner_points(self, chip_area: float, utilization: float = 0.6, 
                              core_utilization: float = 0.7) -> dict:
        """
        Calculate the corner points for die and core areas with PDN considerations.
        """
        # Calculate core area with additional space for PDN
        core_area = (chip_area / utilization) * (1 + self.pdn_margin)
        
        # Ensure minimum width for metal4 straps
        min_side_length = self.metal4_min_width + (2 * self.strap_offset)
        
        # Calculate die area with PDN requirements
        die_area = max(core_area / core_utilization,
                      min_side_length * min_side_length)
        
        # Calculate side lengths ensuring minimum width for PDN
        core_side = max(math.sqrt(core_area), min_side_length)
        die_side = max(math.sqrt(die_area), core_side * 1.2)  # Ensure die is larger than core
        
        # Add padding for power straps
        core_offset = max((die_side - core_side) / 2, self.strap_offset)
        
        # Calculate final corners with PDN considerations
        die_corner = (0, 0, die_side, die_side)
        core_corner = (core_offset, core_offset, 
                      core_offset + core_side, 
                      core_offset + core_side)
        
        # Verify PDN requirements are met
        if (core_corner[2] - core_corner[0]) < self.metal4_min_width:
            raise ValueError("Core width insufficient for PDN requirements")
        
        return {
            'die_area': die_corner,
            'core_area': core_corner,
            'pdn_info': {
                'metal4_width': self.metal4_min_width,
                'strap_offset': self.strap_offset,
                'available_width': core_side
            }
        }

    def run_flow(self, utilization: float = 0.6, core_utilization: float = 0.7) -> None:
        """Run the complete flow with PDN considerations."""
        try:
            # Run Yosys and get chip area
            yosys_output = self.execute_yosys_commands()
            chip_area = self.extract_and_save_area(yosys_output)
            
            if chip_area is not None:
                # Calculate corner points with PDN considerations
                corners = self.calculate_corner_points(chip_area, utilization, core_utilization)
                
                # Print results
                print("\nCorner Points (with PDN considerations):")
                print("Die Area:", corners['die_area'])
                print("Core Area:", corners['core_area'])
                print("\nPDN Information:")
                print(f"Required Metal4 Width: {corners['pdn_info']['metal4_width']} um")
                print(f"Strap Offset: {corners['pdn_info']['strap_offset']} um")
                print(f"Available Width: {corners['pdn_info']['available_width']} um")

        except Exception as e:
            print(f"Error: {str(e)}")

def main():
    # File paths
    liberty_path = "/home/uday_c/OpenROAD/test/Nangate45/Nangate45_typ.lib"
    design_path = "/home/uday_c/OpenROAD/test/risc_v.v"
    top_module = "alu"
    
    calculator = YosysAreaCalculator(liberty_path, design_path, top_module)
    calculator.run_flow()

if __name__ == "__main__":
    main()
