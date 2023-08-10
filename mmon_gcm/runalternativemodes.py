# AUTOGENERATED! DO NOT EDIT! File to edit: ../src/4.2_run_alternative_flux_modes.ipynb.

# %% auto 0
__all__ = ['results_path', 'model_path', 'weightings_csv', 'parameters_csv', 'light_colour', 'atpase_constraint',
           'starch_knockout', 'no_cores', 'model', 'parameters_df', 'arabidopsis_supermodel', 'weightings',
           'temp_results', 'weightings_solution', 'get_file_names_as_integers']

# %% ../src/4.2_run_alternative_flux_modes.ipynb 5
import os
import shutil
import sys
from pathlib import Path

import cobra

# from x import y syntax doesn't work because of nbdev export format
import mmon_gcm.alternativemodes
import mmon_gcm.buildingediting
import mmon_gcm.supermodel
import pandas as pd
from pandarallel import pandarallel

# %% ../src/4.2_run_alternative_flux_modes.ipynb 7
results_path = sys.argv[1]
model_path = sys.argv[2]
weightings_csv = sys.argv[3]
parameters_csv = sys.argv[4]
light_colour = sys.argv[5]
atpase_constraint = sys.argv[6]
starch_knockout = sys.argv[7]
no_cores = int(sys.argv[8])

# %% ../src/4.2_run_alternative_flux_modes.ipynb 8
if light_colour != "blue" and light_colour != "white" and light_colour != "nops":
    raise ValueError(
        f"Please specify either 'blue' or 'white' or 'nops' for light, not {light_colour}"
    )

if atpase_constraint == "True":
    atpase_constraint = True
elif atpase_constraint == "False":
    atpase_constraint = False
else:
    raise ValueError(
        f"Please specify True or False for the ATPase constraint, not {atpase_constraint}"
    )

if starch_knockout == "True":
    starch_knockout = True
elif starch_knockout == "False":
    starch_knockout = False
else:
    raise ValueError(
        f"Please specify True or False for the starck knockout, not {starch_knockout}"
    )

# %% ../src/4.2_run_alternative_flux_modes.ipynb 9
model = cobra.io.load_json_model(model_path)
print("Model imported")

# %% ../src/4.2_run_alternative_flux_modes.ipynb 10
print(model.solver.configuration.tolerances.integrality)
print(model.solver.configuration.tolerances.feasibility)
model.solver.configuration.tolerances.feasibility = (
    1e-8  # 1e-9 takes a long time to solve
)
print(model.solver.configuration.tolerances.feasibility)

# %% ../src/4.2_run_alternative_flux_modes.ipynb 11
parameters_df = pd.read_csv(parameters_csv, index_col=0)

# %% ../src/4.2_run_alternative_flux_modes.ipynb 13
arabidopsis_supermodel = mmon_gcm.supermodel.SuperModel(
    parameters_df.loc[:, "Value"], fba_model=model
)
arabidopsis_supermodel.constrain_osmolarity(printouts=False)
arabidopsis_supermodel.constrain_photons(150, printouts=False)
arabidopsis_supermodel.add_maintenance();

# %% ../src/4.2_run_alternative_flux_modes.ipynb 15
if light_colour == "blue":
    arabidopsis_supermodel.fba_model.reactions.Photon_tx_gc_2.upper_bound = 0
    arabidopsis_supermodel.fba_model.reactions.Photon_tx_me_2.upper_bound = 0
    print("Model constrained with blue light")
elif light_colour == "nops":
    mmon_gcm.buildingediting.set_bounds_multi(
        arabidopsis_supermodel.fba_model, "Photon_tx_gc", 0, 0
    )
    print("Photosynthesis prevented in guard cell")
else:
    print("Model constrained with white light")

if atpase_constraint == True:
    gc_atpase_upper_bound = arabidopsis_supermodel.get_atpase_constraint_value(7.48)
    mmon_gcm.buildingediting.set_bounds_multi(
        arabidopsis_supermodel.fba_model, "PROTON_ATPase_c_gc", 0, gc_atpase_upper_bound
    )
    print("Model ATPase constrained")
else:
    print("Model ATPase left unconstrained")

if starch_knockout == True:
    mmon_gcm.buildingediting.set_bounds_multi(
        arabidopsis_supermodel.fba_model, "RXN_1827_p_gc", 0, 0
    )
    print("Model starch knocked out")
else:
    print("Model starch left unconstrained")

print("Supermodel established and model constrained")

# %% ../src/4.2_run_alternative_flux_modes.ipynb 16
weightings = pd.read_csv(weightings_csv, index_col=[0], header=[0])
print("Weightings file imported")

# %% ../src/4.2_run_alternative_flux_modes.ipynb 20
temp_results = Path(results_path).parent / "_tmp/"

# %% ../src/4.2_run_alternative_flux_modes.ipynb 21
def get_file_names_as_integers(directory_path):
    try:
        # Get a list of all files and directories in the specified directory
        file_list = os.listdir(directory_path)

        # Filter out directories and keep only file names
        file_names_as_integers = [
            int(os.path.splitext(filename)[0])
            for filename in file_list
            if os.path.isfile(os.path.join(directory_path, filename))
        ]

        return file_names_as_integers
    except (OSError, ValueError) as e:
        print(f"An error occurred: {e}")
        return []

# %% ../src/4.2_run_alternative_flux_modes.ipynb 22
if os.path.isdir(temp_results):
    print(f"Already a tmp directory at {temp_results}, checking for existing solutions")
    existing_solutions = get_file_names_as_integers(temp_results)
    print(
        f"There are already {len(existing_solutions)} solutions, dropping these from the weightings csv"
    )

    weightings = weightings.drop(existing_solutions)

else:
    print(
        f"No existing tmp directory at {temp_results}, creating temp directory to store solutions as they come in"
    )
    Path(temp_results).mkdir(parents=True, exist_ok=True)

# %% ../src/4.2_run_alternative_flux_modes.ipynb 23
pandarallel.initialize(nb_workers=no_cores, progress_bar=False)
print(f"Solving model for {len(weightings.index)} alternative weightings")
weightings_solution = weightings.parallel_apply(
    mmon_gcm.alternativemodes.solve_model_with_weightings,
    args=([arabidopsis_supermodel.fba_model, temp_results]),
    axis=1,
)

# %% ../src/4.2_run_alternative_flux_modes.ipynb 24
weightings_solution.to_csv(results_path)
if len(weightings_solution) == len(weightings):
    print(f"All solutions saved to {results_path}")
    print(f"Deleting temp directory {temp_results}")
    shutil.rmtree(temp_results)
