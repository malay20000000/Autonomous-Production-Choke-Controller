from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
import sys

# Add the src directory to path so uvicorn can find the simulator module
sys.path.append(os.path.dirname(__file__))

from simulator import WellSimulator
from controller import ChokeController

app = FastAPI()

# Mount static files
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

sim = WellSimulator()
ctrl = ChokeController()

current_u = 0.0
target_q = 100.0

class TargetRequest(BaseModel):
    target: float

@app.get("/")
def read_landing():
    return FileResponse(os.path.join(static_dir, "landing.html"))

@app.get("/dashboard")
def read_dashboard():
    return FileResponse(os.path.join(static_dir, "index.html"))

@app.post("/api/reset")
def reset_simulation():
    global current_u, target_q
    sim.reset()
    ctrl.reset()
    current_u = 0.0
    target_q = 100.0
    return {"message": "Reset successful"}

@app.post("/api/target")
async def set_target(req: TargetRequest):
    global target_q
    target_q = req.target
    return {"status": "Target updated", "target_q": target_q}

class SettingsRequest(BaseModel):
    du_max: float
    whp_min: float

@app.post("/api/settings")
async def set_settings(req: SettingsRequest):
    ctrl.update_settings(req.du_max, req.whp_min)
    return {"status": "Settings updated", "du_max": ctrl.du_max, "whp_min": ctrl.limits["WHP_min"]}

@app.post("/api/disturb")
def inject_disturbance():
    sim.disturb()
    return {"message": "Disturbance injected"}

@app.get("/api/step")
def step_simulation():
    global current_u
    
    current_state = sim._get_state()
    
    # Calculate next move
    next_u = ctrl.compute_move(target_q, current_state, current_u)
    
    # Step simulation
    q_meas, whp_meas, flp_meas, bhp_meas = sim.step(next_u)
    current_u = next_u
    
    return {
        "target_q": target_q,
        "choke_pct": current_u,
        "q": q_meas,
        "whp": whp_meas,
        "flp": flp_meas,
        "bhp": bhp_meas,
        "limits": ctrl.limits,
        "status_message": getattr(ctrl, "last_status", "Thinking..."),
        "maintenance_cost": getattr(ctrl, "maintenance_cost", 0.0),
        "health_score": getattr(ctrl, "health_score", 100.0)
    }
