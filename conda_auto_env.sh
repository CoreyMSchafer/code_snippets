# Modified from:
# https://github.com/chdoig/conda-auto-env

# Auto activate conda environments
function conda_auto_env() {
  if [ -e "environment.yaml" ]; then
    ENV_NAME=$(head -n 1 environment.yaml | cut -f2 -d ' ')
    # Check if you are already in the environment
    if [[ $CONDA_PREFIX != *$ENV_NAME* ]]; then
      # Try to activate environment
      source activate $ENV_NAME &>/dev/null
    fi
  fi
}

export PROMPT_COMMAND="conda_auto_env;$PROMPT_COMMAND"
