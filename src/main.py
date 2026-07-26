import os
import pandas as pd
import matplotlib.pyplot as plt
from simulator import WellSimulator
from controller import ChokeController

def run_scenario(scenario_name, targets, duration_hrs=50, output_dir="data"):
    sim = WellSimulator()
    ctrl = ChokeController()
    
    sim.reset()
    ctrl.reset()
    
    current_u = 0.0
    history = []
    
    # Run loop
    for t in range(duration_hrs):
        # Determine target Q for this hour based on targets list
        # targets is a list of tuples (start_hour, target_Q)
        target_Q = 0
        for start_hr, q in reversed(targets):
            if t >= start_hr:
                target_Q = q
                break
                
        # Controller computes move
        current_state = sim._get_state()
        next_u = ctrl.compute_move(target_Q, current_state, current_u)
        
        # Step simulator
        q_meas, whp_meas, flp_meas, bhp_meas = sim.step(next_u)
        
        history.append({
            "Time_hr": t,
            "Target_Q": target_Q,
            "Choke_pct": next_u,
            "Q_bbl_hr": q_meas,
            "WHP_psi": whp_meas,
            "FLP_psi": flp_meas,
            "BHP_psi": bhp_meas
        })
        
        current_u = next_u
        
    df = pd.DataFrame(history)
    os.makedirs(output_dir, exist_ok=True)
    csv_path = os.path.join(output_dir, f"{scenario_name}.csv")
    df.to_csv(csv_path, index=False)
    print(f"Scenario {scenario_name} completed and logged to {csv_path}")
    return df

def plot_scenario(df, scenario_name, limits, output_dir="plots"):
    os.makedirs(output_dir, exist_ok=True)
    
    fig, axs = plt.subplots(3, 1, figsize=(10, 12), sharex=True)
    fig.suptitle(f"Scenario: {scenario_name}")
    
    # (a) Target vs Actual Q
    axs[0].plot(df["Time_hr"], df["Target_Q"], 'k--', label="Target Q")
    axs[0].plot(df["Time_hr"], df["Q_bbl_hr"], 'b-', label="Actual Q")
    axs[0].set_ylabel("Flow Rate (bbl/hr)")
    axs[0].legend()
    axs[0].grid(True)
    
    # (b) WHP/FLP/BHP vs limits
    axs[1].plot(df["Time_hr"], df["WHP_psi"], 'g-', label="WHP")
    axs[1].axhline(limits["WHP_min"], color='g', linestyle=':', label="WHP Min")
    axs[1].axhline(limits["WHP_max"], color='g', linestyle='--', label="WHP Max")
    
    axs[1].plot(df["Time_hr"], df["FLP_psi"], 'r-', label="FLP")
    axs[1].axhline(limits["FLP_min"], color='r', linestyle=':', label="FLP Min")
    axs[1].axhline(limits["FLP_max"], color='r', linestyle='--', label="FLP Max")
    
    axs[1].plot(df["Time_hr"], df["BHP_psi"], 'm-', label="BHP")
    axs[1].axhline(limits["BHP_min"], color='m', linestyle=':', label="BHP Min")
    axs[1].axhline(limits["BHP_max"], color='m', linestyle='--', label="BHP Max")
    
    axs[1].set_ylabel("Pressure (psi)")
    axs[1].legend(loc='upper right', bbox_to_anchor=(1.25, 1.0))
    axs[1].grid(True)
    
    # (c) Choke position vs time
    axs[2].plot(df["Time_hr"], df["Choke_pct"], 'orange', label="Choke Position")
    axs[2].set_ylabel("Choke (%)")
    axs[2].set_xlabel("Time (hours)")
    axs[2].set_ylim([0, 100])
    axs[2].legend()
    axs[2].grid(True)
    
    plt.tight_layout(rect=[0, 0, 0.85, 1]) # Adjust for legend
    plot_path = os.path.join(output_dir, f"{scenario_name}.png")
    plt.savefig(plot_path)
    plt.close()
    print(f"Scenario plot saved to {plot_path}")

if __name__ == "__main__":
    ctrl = ChokeController()
    limits = ctrl.limits
    
    # Scenario A: Startup
    print("\nRunning Scenario A: Startup")
    targets_a = [(0, 100)] # Target 100 bbl/hr from start
    df_a = run_scenario("Scenario_A_Startup", targets_a, duration_hrs=30)
    plot_scenario(df_a, "Scenario_A_Startup", limits)
    
    # Scenario B: Target Tracking
    print("\nRunning Scenario B: Target Tracking")
    targets_b = [(0, 100), (25, 150)] # Start 100, then change to 150 at t=25
    df_b = run_scenario("Scenario_B_Target_Tracking", targets_b, duration_hrs=60)
    plot_scenario(df_b, "Scenario_B_Target_Tracking", limits)
    
    # Scenario C: Infeasible Target
    print("\nRunning Scenario C: Infeasible Target")
    targets_c = [(0, 300)] # Request 300 bbl/hr (above safe limits)
    df_c = run_scenario("Scenario_C_Infeasible_Target", targets_c, duration_hrs=40)
    plot_scenario(df_c, "Scenario_C_Infeasible_Target", limits)
