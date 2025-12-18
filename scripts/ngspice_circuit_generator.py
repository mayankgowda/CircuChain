import json
import os

# ==============================================================================
# SPICE GENERATORS FOR EACH TOPOLOGY
# ==============================================================================

def gen_spice_prob1(values, truth):
    # Prob 1: Supermesh
    # Topology: V1-R1-Is-R2-DepSrc-R3-V2
    return f"""* Prob 1: Supermesh (Auto-Generated)
* EXPECTED TRUTH:
* i1 (I(R1)) = {truth['mesh_currents'][0]:.6f} A
* i2 (I(R2)) = {truth['mesh_currents'][1]:.6f} A
* i3 (I(R3)) = {truth['mesh_currents'][2]:.6f} A
* vx (V(2))  = {truth['node_voltages'].get('vx', 0):.4f} V
* vy (V(3))  = {truth['node_voltages'].get('vy', 0):.4f} V

* --- MESH 1 ---
V1 1 0 DC {values['V1']}
R1 1 2 {values['R1']}

* --- SHARED 1-2 (Current Source UP) ---
I_source 0 2 DC {values['Is']}

* --- MESH 2 ---
R2 2 3 {values['R2']}

* --- SHARED 2-3 (Dep Current Source DOWN) ---
* Value = 2 * i1. i1 is current through R1.
* Using Behavioral Source for LTSpice robustness.
B_dep 3 0 I=2*I(R1)

* --- MESH 3 ---
R3 3 4 {values['R3']}
V2 4 0 DC {values['V2']}

.save all
.op
.print op v(2) v(3) I(R1) I(R2) I(R3)
.end
"""

def gen_spice_prob2(values, truth):
    # Prob 2: Opposing Sources
    return f"""* Prob 2: Opposing Sources (Auto-Generated)
* EXPECTED TRUTH:
* i1 (I(R1)) = {truth['mesh_currents'][0]:.6f} A
* i2 (I(R2)) = {truth['mesh_currents'][1]:.6f} A
* v1 (V(2))  = {truth['node_voltages'].get('v1', 0):.4f} V

* --- LEFT LOOP ---
V1 1 0 DC {values['V1']}
R1 1 2 {values['R1']}

* --- SHARED ---
R_share 2 0 {values['R_share']}

* --- RIGHT LOOP ---
R2 2 3 {values['R2']}
V2 3 0 DC {values['V2']}

.save all
.op
.print op v(2) I(R1) I(R2)
.end
"""

def gen_spice_prob3(values, truth):
    # Prob 3: Unbalanced Bridge
    return f"""* Prob 3: Unbalanced Bridge (Auto-Generated)
* EXPECTED TRUTH:
* i1 (I(V_src)) = {truth['mesh_currents'][0]:.6f} A (Approx, Mesh 1 is loop)
* va (V(2))     = {truth['node_voltages'].get('va', 0):.4f} V
* vb (V(3))     = {truth['node_voltages'].get('vb', 0):.4f} V

* --- Source ---
V_src 1 0 DC {values['V']}

* --- Left Leg ---
R_LT 1 2 {values['R_LT']}
R_LB 2 0 {values['R_LB']}

* --- Right Leg ---
R_RT 1 3 {values['R_RT']}
R_RB 3 0 {values['R_RB']}

* --- Bridge ---
R_Br 2 3 {values['R_Br']}

.save all
.op
.print op v(2) v(3) I(V_src)
.end
"""

def gen_spice_prob4(values, truth):
    # Prob 4: Resistive Ladder
    return f"""* Prob 4: Resistive Ladder (Auto-Generated)
* EXPECTED TRUTH:
* i1 (I(R1)) = {truth['mesh_currents'][0]:.6f} A
* i2 (I(R3)) = {truth['mesh_currents'][1]:.6f} A
* i3 (I(R5)) = {truth['mesh_currents'][2]:.6f} A
* v1 (V(2))  = {truth['node_voltages'].get('v1', 0):.4f} V
* v2 (V(3))  = {truth['node_voltages'].get('v2', 0):.4f} V
* v3 (V(4))  = {truth['node_voltages'].get('v3', 0):.4f} V

* --- Mesh 1 ---
V1 1 0 DC {values['V']}
R1 1 2 {values['R1']}
R2 2 0 {values['R2']}

* --- Mesh 2 ---
R3 2 3 {values['R3']}
R4 3 0 {values['R4']}

* --- Mesh 3 ---
R5 3 4 {values['R5']}
R6 4 0 {values['R6']}

.save all
.op
.print op v(2) v(3) v(4) I(R1) I(R3) I(R5)
.end
"""

def gen_spice_prob5(values, truth):
    # Prob 5: Dependent Source
    return f"""* Prob 5: Dependent Source (Auto-Generated)
* EXPECTED TRUTH:
* i1 (I(R1)) = {truth['mesh_currents'][0]:.6f} A
* i2 (I(R2)) = {truth['mesh_currents'][1]:.6f} A
* vx (V(2))  = {truth['node_voltages'].get('vx', 0):.4f} V

* --- Mesh 1 ---
V1 1 0 DC {values['V1']}
R1 1 2 {values['R1']}
R_share 2 0 {values['R_share']}

* --- Mesh 2 ---
* VCVS (Voltage Controlled Voltage Source)
* E_dep N+ N- Control+ Control- Gain
* N+ is Node 3, N- is Node 2 (Top Branch)
* Control is Voltage across R_share (Node 2 to 0)
E_dep 3 2 2 0 {values['k']}

R2 3 0 {values['R2']}

.save all
.op
.print op v(2) I(R1) I(R2)
.end
"""

# ==============================================================================
# MAIN EXECUTION
# ==============================================================================

def generate_all_spice_files(dataset_list, output_dir="spice_verification"):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    print(f"Generating SPICE files in '{output_dir}/'...")
    
    count = 0
    for problem in dataset_list:
        pid = problem['id']
        vals = problem['values']
        truth = problem['ground_truth']
        
        content = ""
        if "Prob1" in pid:
            content = gen_spice_prob1(vals, truth)
        elif "Prob2" in pid:
            content = gen_spice_prob2(vals, truth)
        elif "Prob3" in pid:
            content = gen_spice_prob3(vals, truth)
        elif "Prob4" in pid:
            content = gen_spice_prob4(vals, truth)
        elif "Prob5" in pid:
            content = gen_spice_prob5(vals, truth)
        
        if content:
            filename = f"{output_dir}/{pid}.cir"
            with open(filename, 'w') as f:
                f.write(content)
            count += 1
            
    print(f"Success! Generated {count} .cir files.")
    
    # Zip them for easy download in Colab
    os.system(f"zip -r {output_dir}.zip {output_dir}")
    print(f"Zipped archive created: {output_dir}.zip")

# --- Run ---
if __name__ == "__main__":
    # Assumes 'dataset' variable exists from previous step
    # If loading from file:
    # with open('circuchain_dataset_100.json', 'r') as f: dataset = json.load(f)
    generate_all_spice_files(dataset)