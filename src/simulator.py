import math
import time

class WellSimulator:
    """
    Placeholder simulator for a naturally flowing oil well.
    Models nonlinear choke-to-flow and pressure behavior with first-order lag.
    
    This is a stand-in and should be swapped for the official Honeywell simulator.
    """
    def __init__(self):
        # Reservoir and system constants
        self.Pr = 3000.0        # Reservoir pressure, psi
        self.Psep = 200.0       # Separator pressure, psi
        self.k_res = 2.0        # Productivity index related pressure drop, psi / (bbl/hr)
        self.k_tubing = 0.01    # Tubing friction factor, psi / (bbl/hr)^2
        self.k_flowline = 0.005 # Flowline friction factor, psi / (bbl/hr)^2
        self.Q_max = 250.0      # Maximum flow rate, bbl/hr
        
        # Dynamics
        self.Ts = 1.0           # Sample time, hr
        self.tau = 2.0          # Time constant, hr
        self.alpha = math.exp(-self.Ts / self.tau)
        
        self.reset()
        
    def reset(self):
        """Reset the simulator to zero flow steady state."""
        self.Q = 0.0
        self.WHP = 329.1  # Extrapolated static WHP from dataset
        self.FLP = 218.1  # Extrapolated static FLP from dataset
        self.BHP = 3356.6 # Extrapolated static BHP from dataset
        self.q_disturb = 0.0 # Flow rate disturbance
        return self._get_state()
        
    def disturb(self):
        """Simulate a sudden geological disturbance (pressure/flow drop)."""
        self.q_disturb -= 40.0
        self.Q = max(0.0, self.Q - 40.0) # Instantly crash the current flow for visual effect
        
    def step(self, choke_position: float) -> tuple[float, float, float, float]:
        """
        Step the simulator forward by one time step (Ts).
        
        Args:
            choke_position: Choke opening in percent (0 to 100)
            
        Returns:
            Tuple of (Q, WHP, FLP, BHP)
            Q in bbl/hr; WHP, FLP, BHP in psi
        """
        # Clamp choke position
        u = max(0.0, min(100.0, choke_position))
        
        # Calculate steady state flow for this choke position
        u = max(0.0, min(100.0, choke_position))
        
        # Polynomials extracted directly from the dataset's steady states
        # The dataset only covers 30% to 65%. For u < 30, we linearly interpolate to 0.
        if u < 30.0:
            Q_ss = u * (93.72 / 30.0)
        else:
            Q_ss = -0.002646 * u**2 + 2.049 * u + 34.25
            
        # Apply geological disturbance
        Q_ss += self.q_disturb
            
        Q_ss = max(0.0, Q_ss) # Ensure non-negative flow
        
        WHP_ss = -0.001493 * Q_ss**2 - 0.4855 * Q_ss + 329.1
        FLP_ss = -0.001297 * Q_ss**2 - 0.2009 * Q_ss + 218.1
        BHP_ss = -0.01101 * Q_ss**2 - 1.302 * Q_ss + 3356.6
        
        # Apply first-order lag to flow
        self.Q = self.alpha * self.Q + (1.0 - self.alpha) * Q_ss
        
        # Apply first-order lag to pressures
        self.WHP = self.alpha * self.WHP + (1.0 - self.alpha) * WHP_ss
        self.FLP = self.alpha * self.FLP + (1.0 - self.alpha) * FLP_ss
        self.BHP = self.alpha * self.BHP + (1.0 - self.alpha) * BHP_ss
        
        # A real choke equation would match (WHP - FLP) to flow, 
        # but for this placeholder, we just map it algebraically for stability.
        
        return self._get_state()
        
    def _get_state(self) -> tuple[float, float, float, float]:
        return (self.Q, self.WHP, self.FLP, self.BHP)


if __name__ == "__main__":
    print("Testing Placeholder WellSimulator...")
    sim = WellSimulator()
    print("Initial State (Choke=0%): Q={:.2f}, WHP={:.2f}, FLP={:.2f}, BHP={:.2f}".format(*sim.reset()))
    
    print("\nStepping choke to 50% (5% at a time)...")
    u_test = 0.0
    for i in range(1, 11):
        u_test += 5.0
        q, whp, flp, bhp = sim.step(u_test)
        print(f"Hour {i:2d} | u={u_test:4.1f}% | Q={q:6.2f} bbl/hr | WHP={whp:7.2f} psi | FLP={flp:6.2f} psi | BHP={bhp:7.2f} psi")
        
    print("\nStepping choke to 100% (5% at a time)...")
    for i in range(11, 21):
        u_test += 5.0
        q, whp, flp, bhp = sim.step(u_test)
        print(f"Hour {i:2d} | u={u_test:4.1f}% | Q={q:6.2f} bbl/hr | WHP={whp:7.2f} psi | FLP={flp:6.2f} psi | BHP={bhp:7.2f} psi")
