import sys
import pathlib

# Run the configuration script when the user runs 
# python3 -m asi [init, config, or configure]

here = pathlib.Path(__file__).parent.resolve()


if (len(sys.argv) > 1) and (sys.argv[1] in ['init', 'initialize', 'config', 'configure']):
    print('Running the configuration script.')
    # SAMPEX Data dir
    s = (f'What is the aurora data directory? Press enter to not specify. '
         f'If the directory is not specified, /aurora_asi/data/ folder will be created.')
    asi_data_dir = input(s)
    
    # If the user specified the directory, check that the ASI directory already exists 
    # and make that directory if it does not.
    if asi_data_dir != '':
        if not pathlib.Path(asi_data_dir).exists():
            pathlib.Path(asi_data_dir).mkdir(parents=True)
            print(f'Made aurora_asi data directory at {pathlib.Path(asi_data_dir)}.')
        else:
            print(f'aurora_asi data directory at {pathlib.Path(asi_data_dir)} already exists.')
    else:
        # If the user did not specify the directory, make one at /aurora_asi/data/
        asi_data_dir = here.parents[0] / 'data'
        if not asi_data_dir.exists():
            asi_data_dir.mkdir()
            print(f'aurora_asi directory at {asi_data_dir} created.')
        else:
            print(f'aurora_asi directory at {asi_data_dir} already exists.')

    # Finally write the Python code to be later imported.
    with open(pathlib.Path(here, 'config.py'), 'w') as f:
        f.write('import pathlib\n\n')
        f.write(f'PROJECT_DIR = pathlib.Path("{here}")\n')
        f.write(f'ASI_DATA_DIR = pathlib.Path("{asi_data_dir}")\n')

else:
    print('This is a configuration script to set up config.py file. The config '
        'file will contain the aurora data directory, and the base project '
        'directory (here). To get the prompt after this package is installed, run '
        'python3 -m asi init')
