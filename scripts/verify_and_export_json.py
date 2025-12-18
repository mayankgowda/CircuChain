import json
import os
import re
import subprocess
import shutil

# ==============================================================================
# CONFIGURATION
# ==============================================================================
SPICE_DIR = "spice_verification"
LOG_DIR = "spice_logs"
NGSPICE_CMD = "ngspice" 
DATASET_FILE = "circuchain_full_dataset_2.json"

# ==============================================================================
# 1. ROBUST GENERATOR (Produces clean .cir files)
# ==============================================================================
def gen_spice_prob1(values, truth):
    return f"""* Prob 1: Supermesh
* EXPECTED TRUTH:
* i1 (i(v_sense_i1)) = {truth['mesh_currents'][0]:.6f}
* i2 (i(v_sense_i2)) = {truth['mesh_currents'][1]:.6f}
* i3 (i(v_sense_i3)) = {truth['mesh_currents'][2]:.6f}
* vx (v(2))  = {truth['node_voltages'].get('vx', 0):.4f}
* vy (v(3))  = {truth['node_voltages'].get('vy', 0):.4f}

V1 1 0 DC {values['V1']}
R1 1 1_sense {values['R1']}
V_sense_i1 1_sense 2 DC 0

I_source 0 2 DC {values['Is']}

R2 2 2_sense {values['R2']}
V_sense_i2 2_sense 3 DC 0

F_dep 3 0 V_sense_i1 2

R3 3 3_sense {values['R3']}
V_sense_i3 3_sense 4 DC 0

V2 4 0 DC {values['V2']}

.op
.print op v(2) v(3) i(v_sense_i1) i(v_sense_i2) i(v_sense_i3)
.end
"""

def gen_spice_prob2(values, truth):
    return f"""* Prob 2: Opposing
* EXPECTED TRUTH:
* i1 (i(v_sense_i1)) = {truth['mesh_currents'][0]:.6f}
* i2 (i(v_sense_i2)) = {truth['mesh_currents'][1]:.6f}
* v1 (v(2))  = {truth['node_voltages'].get('v1', 0):.4f}

V1 1 0 DC {values['V1']}
R1 1 1_sense {values['R1']}
V_sense_i1 1_sense 2 DC 0

R_share 2 0 {values['R_share']}

R2 2 2_sense {values['R2']}
V_sense_i2 2_sense 3 DC 0

V2 3 0 DC {values['V2']}

.op
.print op v(2) i(v_sense_i1) i(v_sense_i2)
.end
"""

def gen_spice_prob3(values, truth):
    return f"""* Prob 3: Bridge
* EXPECTED TRUTH:
* i1 (i(v_sense_i1)) = {truth['mesh_currents'][0]:.6f}
* va (v(2))     = {truth['node_voltages'].get('va', 0):.4f}
* vb (v(3))     = {truth['node_voltages'].get('vb', 0):.4f}

V_src 1_src 0 DC {values['V']}
V_sense_i1 1_src 1 DC 0

R_LT 1 2 {values['R_LT']}
R_LB 2 0 {values['R_LB']}

R_RT 1 3 {values['R_RT']}
R_RB 3 0 {values['R_RB']}

R_Br 2 3 {values['R_Br']}

.op
.print op v(2) v(3) i(v_sense_i1)
.end
"""

def gen_spice_prob4(values, truth):
    return f"""* Prob 4: Ladder
* EXPECTED TRUTH:
* i1 (i(v_sense_i1)) = {truth['mesh_currents'][0]:.6f}
* i2 (i(v_sense_i2)) = {truth['mesh_currents'][1]:.6f}
* i3 (i(v_sense_i3)) = {truth['mesh_currents'][2]:.6f}
* v1 (v(2))  = {truth['node_voltages'].get('v1', 0):.4f}
* v2 (v(3))  = {truth['node_voltages'].get('v2', 0):.4f}
* v3 (v(4))  = {truth['node_voltages'].get('v3', 0):.4f}

V1 1 0 DC {values['V']}
R1 1 1_sense {values['R1']}
V_sense_i1 1_sense 2 DC 0
R2 2 0 {values['R2']}

R3 2 2_sense {values['R3']}
V_sense_i2 2_sense 3 DC 0
R4 3 0 {values['R4']}

R5 3 3_sense {values['R5']}
V_sense_i3 3_sense 4 DC 0
R6 4 0 {values['R6']}

.op
.print op v(2) v(3) v(4) i(v_sense_i1) i(v_sense_i2) i(v_sense_i3)
.end
"""

def gen_spice_prob5(values, truth):
    return f"""* Prob 5: Dependent
* EXPECTED TRUTH:
* i1 (i(v_sense_i1)) = {truth['mesh_currents'][0]:.6f}
* i2 (i(v_sense_i2)) = {truth['mesh_currents'][1]:.6f}
* vx (v(2))  = {truth['node_voltages'].get('vx', 0):.4f}

V1 1 0 DC {values['V1']}
R1 1 1_sense {values['R1']}
V_sense_i1 1_sense 2 DC 0
R_share 2 0 {values['R_share']}

E_dep 3 2 2 0 {values['k']}

R2 3 3_sense {values['R2']}
V_sense_i2 3_sense 0 DC 0

.op
.print op v(2) i(v_sense_i1) i(v_sense_i2)
.end
"""

# ==============================================================================
# 2. UNIVERSAL PARSER (Handles Tables & Equations)
# ==============================================================================
def parse_log_universal(log_path):
    results = {}
    if not os.path.exists(log_path): return {}
    
    with open(log_path, 'r', errors='ignore') as f: 
        lines = f.readlines()
    
    re_eq = re.compile(r"([a-z0-9_\(\)]+)\s*=\s*([-+]?[\d\.]+(?:e[-+]?\d+)?)", re.IGNORECASE)
    re_table = re.compile(r"^\s*([a-z0-9_#\(\)]+)\s+([-+]?[\d\.]+(?:e[-+]?\d+)?)", re.IGNORECASE)

    for line in lines:
        line = line.strip()
        if not line: continue
        
        m_eq = re_eq.search(line)
        if m_eq:
            label = m_eq.group(1).lower()
            val = float(m_eq.group(2))
            results[label] = val
            continue
            
        m_tab = re_table.search(line)
        if m_tab:
            label = m_tab.group(1).lower()
            val = float(m_tab.group(2))
            
            if "#branch" in label:
                device = label.split("#")[0]
                results[f"i({device})"] = val 
                results[label] = val
            else:
                results[label] = val

    return results

def parse_truth(cir_path):
    targets = {}
    with open(cir_path, 'r') as f: content = f.read()
    pattern = r"\*\s+\w+\s+\((.+?)\)\s+=\s+([-+]?[\d\.]+)"
    for m in re.finditer(pattern, content):
        targets[m.group(1).lower()] = float(m.group(2))
    return targets

# ==============================================================================
# 3. MASTER RUNNER
# ==============================================================================
def run_master_verification():
    try:
        with open(DATASET_FILE, 'r') as f: dataset = json.load(f)
    except:
        print(f"Dataset file '{DATASET_FILE}' not found!")
        return

    # Clean dirs
    if os.path.exists(SPICE_DIR): shutil.rmtree(SPICE_DIR)
    os.makedirs(SPICE_DIR)
    if os.path.exists(LOG_DIR): shutil.rmtree(LOG_DIR)
    os.makedirs(LOG_DIR)

    # 1. Regenerate
    for p in dataset:
        pid = p['id']; val = p['values']; truth = p['ground_truth']
        if "Prob1" in pid: c = gen_spice_prob1(val, truth)
        elif "Prob2" in pid: c = gen_spice_prob2(val, truth)
        elif "Prob3" in pid: c = gen_spice_prob3(val, truth)
        elif "Prob4" in pid: c = gen_spice_prob4(val, truth)
        elif "Prob5" in pid: c = gen_spice_prob5(val, truth)
        with open(f"{SPICE_DIR}/{pid}.cir", 'w') as f: f.write(c)
    
    files = sorted([f for f in os.listdir(SPICE_DIR) if f.endswith('.cir')])
    
    # 2. Run & Verify
    final_output = []
    
    for fname in files:
        cir_path = os.path.join(SPICE_DIR, fname)
        log_path = os.path.join(LOG_DIR, fname.replace('.cir', '.log'))

        # Run NGSPICE
        try:
            subprocess.run([NGSPICE_CMD, '-b', '-o', log_path, cir_path], 
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            # Add error entry
            final_output.append({
                "id": fname.replace(".cir", ""),
                "status": "ERROR",
                "message": str(e)
            })
            continue

        truth = parse_truth(cir_path)
        actual = parse_log_universal(log_path)
        
        # Verify
        file_errs = []
        # Filter actual to only show keys relevant to verification for cleaner JSON
        relevant_actual = {} 
        
        for k, v_exp in truth.items():
            v_act = actual.get(k)
            relevant_actual[k] = v_act # Store what we found
            
            if v_act is None:
                file_errs.append(f"Missing {k}")
                continue
            
            err = abs(v_act - v_exp)
            if not (err < 1e-5 or (err/(abs(v_exp)+1e-9)) < 0.05):
                file_errs.append(f"{k}: Exp {v_exp} != Act {v_act}")
        
        status = "PASS" if not file_errs else "FAIL"
        
        # Add to result list
        final_output.append({
            "id": fname.replace(".cir", ""),
            "status": status,
            "verifier_map": truth,
            "spice_values": relevant_actual,
            "errors": file_errs
        })

    # 3. Print JSON
    print(json.dumps(final_output, indent=2))
    
    # Also save to file
    with open("verification_results.json", "w") as f:
        json.dump(final_output, f, indent=2)

if __name__ == "__main__":
    run_master_verification()