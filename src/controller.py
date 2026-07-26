import numpy as np
import math

class ChokeController:
    def __init__(self):
        # We will dynamically fit the models once during init (or we could load from a file)
        # For speed in this challenge, we just run a quick short test or we can hardcode the K values.
        # To be safe and fast, let's just use the gains around 50%.
        # From the physics:
        # Q_ss = 250 * (u/100)^0.65. At u=50, Q=160. At u=60, Q=179. DeltaQ = 19. K_q = 1.9 bbl/hr / %
        # BHP = 3000 - 2 * Q -> K_bhp = -2 * 1.9 = -3.8 psi / %
        # WHP = BHP - 0.01 * Q^2 -> K_whp approx -3.8 - 0.01*(2*160*1.9) = -9.88 psi / %
        # FLP = 200 + 0.005 * Q^2 -> K_flp approx 0 + 0.005*(2*160*1.9) = 3.04 psi / %
        
        self.models = {
            "Q": {"K": 1.90, "tau": 2.0},
            "WHP": {"K": -10.0, "tau": 2.0},
            "FLP": {"K": 3.0, "tau": 2.0},
            "BHP": {"K": -3.8, "tau": 2.0}
        }
        
        # Constraints based on realistic dataset pressures
        self.limits = {
            "WHP_min": 100.0,
            "WHP_max": 500.0,
            "FLP_min": 100.0,
            "FLP_max": 250.0,
            "BHP_min": 2500.0,
            "BHP_max": 3500.0
        }
        
        # Actuator limits
        self.u_min = 0.0
        self.u_max = 100.0
        self.du_max = 5.0  # max 5% per hour
        self.Ts = 1.0
        
        # State tracking for the model
        self.u_last = 0.0
        self.q_pred = 0.0
        self.whp_pred = 3000.0
        self.flp_pred = 200.0
        self.bhp_pred = 3000.0
        self.last_status = "System Ready."
        self.maintenance_cost = 0.0
        self.health_score = 100.0
        
    def reset(self):
        self.u_last = 0.0
        self.q_pred = 0.0
        self.whp_pred = 329.1
        self.flp_pred = 218.1
        self.bhp_pred = 3356.6
        self.last_status = "Simulation Reset."
        self.maintenance_cost = 0.0
        self.health_score = 100.0

    def update_settings(self, du_max: float, whp_min: float):
        """Allows dynamic tuning of AI behavior and physics constraints."""
        self.du_max = max(0.5, min(20.0, du_max))
        self.limits["WHP_min"] = max(50.0, min(500.0, whp_min))
        self.last_status = f"AI Settings Updated: Agility {self.du_max}%, WHP Limit {self.limits['WHP_min']} psi."

    def update_models(self, current_u: float):
        """
        Dynamically calculates the process gains (Jacobian) based on the current choke position.
        This fixes the Nonlinear Model Mismatch problem!
        """
        u_eff = max(0.1, current_u)
        
        # Handle analytical derivatives for the low choke interpolation
        if u_eff < 30.0:
            K_q = 93.72 / 30.0
            q_approx = u_eff * K_q
        else:
            K_q = -0.005292 * u_eff + 2.049
            q_approx = -0.002646 * u_eff**2 + 2.049 * u_eff + 34.25
        
        # Pressure derivatives (chain rule: dP/du = dP/dQ * dQ/du)
        K_whp = (-0.002986 * q_approx - 0.4855) * K_q
        K_flp = (-0.002594 * q_approx - 0.2009) * K_q
        K_bhp = (-0.02202 * q_approx - 1.302) * K_q
        
        self.models["Q"]["K"] = K_q
        self.models["WHP"]["K"] = K_whp
        self.models["FLP"]["K"] = K_flp
        self.models["BHP"]["K"] = K_bhp

    def compute_move(self, target_Q: float, current_state: tuple[float, float, float, float], current_u: float) -> float:
        """
        Calculates the next choke position.
        current_state = (Q, WHP, FLP, BHP)
        """
        # Update the AI's math model dynamically before making a decision (Gain Scheduling)
        self.update_models(current_u)
        
        Q_meas, WHP_meas, FLP_meas, BHP_meas = current_state
        
        # Grid search over candidate moves with fine resolution (0.1% steps) to prevent hunting/wobbling
        candidates = np.linspace(-self.du_max, self.du_max, 101)
        
        best_u = current_u
        best_error = float('inf')
        
        alpha = math.exp(-self.Ts / 2.0)
        
        for du in candidates:
            u_cand = current_u + du
            
            # Check hard limits
            if u_cand < self.u_min or u_cand > self.u_max:
                continue
                
            # We predict the future steady state to ensure we don't violate limits eventually
            whp_ss = WHP_meas + self.models["WHP"]["K"] * du
            flp_ss = FLP_meas + self.models["FLP"]["K"] * du
            bhp_ss = BHP_meas + self.models["BHP"]["K"] * du
            q_ss = Q_meas + self.models["Q"]["K"] * du
            
            # Also predict t+1 for the objective function tracking
            q_next = alpha * Q_meas + (1 - alpha) * q_ss
            
            # Check constraints on predicted steady state (safety first!)
            if whp_ss < self.limits["WHP_min"] or whp_ss > self.limits["WHP_max"]:
                continue
            if flp_ss < self.limits["FLP_min"] or flp_ss > self.limits["FLP_max"]:
                continue
            if bhp_ss < self.limits["BHP_min"] or bhp_ss > self.limits["BHP_max"]:
                continue
                
            # Objective: Minimize error to target, with a small move suppression penalty for extreme stability
            move_penalty = 0.5
            error = abs(q_next - target_Q) + move_penalty * abs(du)
            
            if error < best_error:
                best_error = error
                best_u = u_cand
                
        # Determine status message
        if abs(Q_meas - target_Q) < 0.5 and abs(best_u - current_u) < 0.1:
            self.last_status = f"Target flow rate ({target_Q} bbl/hr) achieved and stabilized."
        elif best_u > current_u:
            self.last_status = f"Opening choke to increase flow towards Target ({target_Q} bbl/hr)."
        elif best_u < current_u:
            self.last_status = f"Choking back to reduce flow towards Target ({target_Q} bbl/hr)."
        else:
            self.last_status = f"Holding steady. Target: {target_Q} bbl/hr."
            
        # Check if we are near any safety constraints
        if WHP_meas < self.limits["WHP_min"] * 1.1:
            self.last_status = f"WARNING: WHP approaching minimum constraint ({WHP_meas:.1f} psi). Slowing choke movement."
        elif FLP_meas > self.limits["FLP_max"] * 0.9:
            self.last_status = f"WARNING: FLP approaching maximum constraint ({FLP_meas:.1f} psi). Slowing choke movement."
            
        # Calculate maintenance cost (₹100 per 1% of choke movement)
        delta_u = abs(best_u - current_u)
        if delta_u > 0.01:
            self.maintenance_cost += delta_u * 100.0
            
        # Calculate AI Health Score
        health = 100.0
        # Penalty for target error
        error_penalty = min(60.0, abs(Q_meas - target_Q) * 2.0)
        health -= error_penalty
        
        # Heavy penalty for being near dangerous pressures
        if WHP_meas < self.limits["WHP_min"] + 50:
            health -= 30.0
        if FLP_meas > self.limits["FLP_max"] - 20:
            health -= 30.0
            
        self.health_score = max(0.0, min(100.0, health))
            
        self.u_last = best_u
        return best_u

if __name__ == "__main__":
    print("Testing Controller...")
    ctrl = ChokeController()
    state = (160.0, 2400.0, 320.0, 2680.0) # Dummy state
    u = ctrl.compute_move(180.0, state, 50.0)
    print(f"Current u: 50.0, Target Q: 180.0, Next u: {u}")
