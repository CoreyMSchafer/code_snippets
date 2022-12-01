# code_snippets
## Flask-SQLAlchemy Version 3.0.0 update
- An active Flask application context is always required to access `session` and `engine`, regardless of if an application was passed to the constructor.
- Without an application context, creating db from terminal will raise `RuntimeError: Working outside of application context.` when you try to invoke `db.create_all()` from python interpreter.
- To counteract this issue, two solutions are presented:
  1. `flask shell` offers made-ready app context and instance to create db.
  2. Import app from FlaskBlog and create db under app context:
    ```
    from flaskblog import app
    with app.app_context():
        db.create_all()
    ```