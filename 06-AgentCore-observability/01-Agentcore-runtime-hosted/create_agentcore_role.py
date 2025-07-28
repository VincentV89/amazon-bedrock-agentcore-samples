import sys
import os

# Get the current notebook's directory
current_dir = os.path.dirname(os.path.abspath('__file__' if '__file__' in globals() else '.'))

# Navigate up to the utils.py location
utils_dir = os.path.join(current_dir, '..')
utils_dir = os.path.abspath(utils_dir)

# Add to sys.path
sys.path.insert(0, utils_dir)

from utils import create_agentcore_role

agent_name="strands_claude"
agentcore_iam_role = create_agentcore_role(agent_name=agent_name)
