"""
Entry point for running SANS webapp via `python -m sans_webapp` or `sans-webapp` command.
"""

import sys
from pathlib import Path


def main() -> None:
    """Run the Streamlit application."""
    try:
        from streamlit.web import cli as stcli
    except ImportError:
        print('Error: Streamlit is not installed. Please install it with: pip install streamlit')
        sys.exit(1)

    # Get the path to the app.py file within this package
    app_path = Path(__file__).parent / 'app.py'

    if not app_path.exists():
        print(f'Error: Could not find app.py at {app_path}')
        sys.exit(1)

    # Run streamlit with the app
    sys.argv = ['streamlit', 'run', str(app_path), '--server.headless=true'] + sys.argv[1:]
    sys.exit(stcli.main())


if __name__ == '__main__':
    main()
