import nbformat as nbf
import os

nb = nbf.v4.new_notebook()

cells = []

# Cell 1
cells.append(nbf.v4.new_markdown_cell("""# Open Loop Analysis
This notebook performs step tests on the placeholder well simulator to generate open-loop response data, plots steady-state gain curves, and fits simple FOPDT/First-order models for the predictive controller."""))

# Cell 2
cells.append(nbf.v4.new_code_cell("""import sys
import os
sys.path.append(os.path.abspath('../src'))
import model_id
import pandas as pd
import matplotlib.pyplot as plt"""))

# Cell 3
cells.append(nbf.v4.new_markdown_cell("## 1. Run Step Tests\nStepping the choke from 0 to 100% in 10% increments, allowing 15 hours per step to reach steady state."))
cells.append(nbf.v4.new_code_cell("""# Run tests and save to data directory
df = model_id.run_step_tests(output_data_path='../data/step_test_data.csv')
df.head()"""))

# Cell 4
cells.append(nbf.v4.new_markdown_cell("## 2. Plot Gain Curves\nPlot the steady-state value of Q, WHP, FLP, and BHP against the choke opening."))
cells.append(nbf.v4.new_code_cell("""model_id.plot_gain_curves(df, output_plot_dir='../plots')

# Display the saved plot in the notebook
from IPython.display import Image, display
display(Image(filename='../plots/gain_curves.png'))"""))

# Cell 5
cells.append(nbf.v4.new_markdown_cell("## 3. Fit First-Order Models\nFit a simple first-order model for a step change around the operating point (e.g., 50% to 60%). This will provide the gains ($K$) and time constants ($\\tau$) for the predictive controller."))
cells.append(nbf.v4.new_code_cell("""models = model_id.fit_first_order_models(df)"""))

nb['cells'] = cells

os.makedirs('notebooks', exist_ok=True)
with open('notebooks/open_loop_analysis.ipynb', 'w') as f:
    nbf.write(nb, f)
print("Notebook created.")
