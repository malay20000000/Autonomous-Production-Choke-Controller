import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
from simulator import WellSimulator

def first_order_step_response(t, K, tau, y0):
    """First-order step response function: y(t) = y0 + K * (1 - exp(-t/tau))."""
    return y0 + K * (1 - np.exp(-t / tau))

def run_step_tests(output_data_path="data/step_test_data.csv"):
    """Runs a series of step tests on the simulator and saves to CSV."""
    sim = WellSimulator()
    
    # We will step the choke from 0 to 100 in increments of 5% to respect the 5% maximum movement rule
    # We allow 15 hours per step to reach steady state
    
    history = []
    t = 0
    
    for choke in range(0, 101, 5):
        for _ in range(15):
            q, whp, flp, bhp = sim.step(float(choke))
            history.append({
                "Time_hr": t,
                "Choke_pct": choke,
                "Q_bbl_hr": q,
                "WHP_psi": whp,
                "FLP_psi": flp,
                "BHP_psi": bhp
            })
            t += 1
            
    df = pd.DataFrame(history)
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(output_data_path), exist_ok=True)
    df.to_csv(output_data_path, index=False)
    print(f"Step test data saved to {output_data_path}")
    return df

def plot_gain_curves(df, output_plot_dir="plots"):
    """Plots steady state values vs choke position (gain curves)."""
    os.makedirs(output_plot_dir, exist_ok=True)
    
    # Extract steady state values (last hour of each choke step)
    df_ss = df.groupby("Choke_pct").last().reset_index()
    
    fig, axs = plt.subplots(2, 2, figsize=(12, 8))
    fig.suptitle('Steady State Gain Curves vs Choke Opening')
    
    axs[0, 0].plot(df_ss["Choke_pct"], df_ss["Q_bbl_hr"], marker='o', color='b')
    axs[0, 0].set_title('Flow Rate (Q) vs Choke')
    axs[0, 0].set_ylabel('Q (bbl/hr)')
    axs[0, 0].grid(True)
    
    axs[0, 1].plot(df_ss["Choke_pct"], df_ss["WHP_psi"], marker='o', color='g')
    axs[0, 1].set_title('Wellhead Pressure (WHP) vs Choke')
    axs[0, 1].set_ylabel('WHP (psi)')
    axs[0, 1].grid(True)
    
    axs[1, 0].plot(df_ss["Choke_pct"], df_ss["FLP_psi"], marker='o', color='r')
    axs[1, 0].set_title('Flowline Pressure (FLP) vs Choke')
    axs[1, 0].set_ylabel('FLP (psi)')
    axs[1, 0].set_xlabel('Choke (%)')
    axs[1, 0].grid(True)
    
    axs[1, 1].plot(df_ss["Choke_pct"], df_ss["BHP_psi"], marker='o', color='purple')
    axs[1, 1].set_title('Bottomhole Pressure (BHP) vs Choke')
    axs[1, 1].set_ylabel('BHP (psi)')
    axs[1, 1].set_xlabel('Choke (%)')
    axs[1, 1].grid(True)
    
    plt.tight_layout()
    plot_path = os.path.join(output_plot_dir, "gain_curves.png")
    plt.savefig(plot_path)
    plt.close()
    print(f"Gain curves plot saved to {plot_path}")
    
def fit_first_order_models(df):
    """Fits simple first-order models around the operating point of 50% choke."""
    # Let's extract the step response from 50% to 55%
    df_step = df[(df["Choke_pct"] == 55) | (df["Choke_pct"] == 50)].copy()
    
    # We want only the transient from 50 to 55. The step starts at the first 55% row.
    t_start = df_step[df_step["Choke_pct"] == 55]["Time_hr"].min()
    
    # Get steady state values at 50%
    y0_vals = df_step[df_step["Time_hr"] == (t_start - 1)].iloc[0]
    
    # Get the 55% transient data
    transient = df_step[df_step["Choke_pct"] == 55].copy()
    transient["t_rel"] = transient["Time_hr"] - t_start + 1 # +1 so first step is t=1
    
    t_data = transient["t_rel"].values
    
    models = {}
    
    print("\n--- FITTED FOPDT/FIRST ORDER PARAMETERS (50% -> 55% Step) ---")
    for var in ["Q_bbl_hr", "WHP_psi", "FLP_psi", "BHP_psi"]:
        y_data = transient[var].values
        y0 = y0_vals[var]
        
        # Estimate delta Y for bounds and K guess
        y_ss = y_data[-1]
        delta_y = y_ss - y0
        delta_u = 5.0 # 55% - 50%
        
        K_guess = delta_y / delta_u
        
        try:
            # We fix y0 and fit K and tau
            # Curve fit: y(t) = y0 + K*delta_u * (1 - exp(-t/tau))
            # Let's redefine fit function to include delta_u
            def fit_func(t, K, tau):
                return y0 + K * delta_u * (1 - np.exp(-t / tau))
                
            popt, _ = curve_fit(fit_func, t_data, y_data, p0=[K_guess, 2.0], bounds=([-np.inf, 0.1], [np.inf, 10.0]))
            K_fit, tau_fit = popt
            
            models[var] = {"K": K_fit, "tau": tau_fit, "y0": y0}
            print(f"{var:10s} : K = {K_fit:8.3f}, tau = {tau_fit:4.2f} hr")
            
        except Exception as e:
            print(f"Failed to fit {var}: {e}")
            
    return models

if __name__ == "__main__":
    df = run_step_tests(output_data_path="../data/step_test_data.csv")
    plot_gain_curves(df, output_plot_dir="../plots")
    fit_first_order_models(df)
