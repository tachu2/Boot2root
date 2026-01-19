import math
import re

def parse_turtle_file(filename):
    commands = []
    try:
        with open(filename, 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"Error: {filename} not found.")
        return []
        
    for line in lines:
        line = line.strip()
        if not line or "cat" in line: continue # Skip empty lines and shell echoes
        
        # Match French turtle commands
        if "Avance" in line:
            match = re.search(r"Avance (\d+) spaces", line)
            if match: commands.append(('move', int(match.group(1))))
        elif "Recule" in line:
            match = re.search(r"Recule (\d+) spaces", line)
            if match: commands.append(('move', -int(match.group(1))))
        elif "Tourne gauche" in line:
            match = re.search(r"Tourne gauche de (\d+) degrees", line)
            if match: commands.append(('turn', int(match.group(1))))
        elif "Tourne droite" in line:
            match = re.search(r"Tourne droite de (\d+) degrees", line)
            if match: commands.append(('turn', -int(match.group(1))))
    return commands

def generate_svg(commands, output_file="turtle_result.svg"):
    if not commands:
        print("No commands to draw.")
        return

    x, y = 0, 0
    angle = -90 # SVG coordinate system: 0 degrees is Right, 90 is Down. Starting UP = -90.
    
    path_data = "M 0 0"
    coords = [(0, 0)]
    
    for cmd, value in commands:
        if cmd == 'move':
            rad = math.radians(angle)
            x += value * math.cos(rad)
            y += value * math.sin(rad)
            path_data += f" L {x:.2f} {y:.2f}"
            coords.append((x, y))
        elif cmd == 'turn':
            angle -= value # Left turn decreases angle in clockwise system
            
    # Calculate bounding box for the viewBox
    min_x = min(c[0] for c in coords)
    max_x = max(c[0] for c in coords)
    min_y = min(c[1] for c in coords)
    max_y = max(c[1] for c in coords)
    
    width = max_x - min_x + 20
    height = max_y - min_y + 20
    view_box = f"{min_x - 10} {min_y - 10} {width} {height}"
    
    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view_box}" style="background-color:white;">
    <path d="{path_data}" stroke="black" stroke-width="2" fill="none" stroke-linejoin="round" stroke-linecap="round" />
</svg>'''

    with open(output_file, 'w') as f:
        f.write(svg_content)
    print(f"Successfully generated {output_file}")

if __name__ == "__main__":
    # Ensure the input file exists
    input_file = 'turtle_downloaded.txt'
    cmds = parse_turtle_file(input_file)
    generate_svg(cmds)