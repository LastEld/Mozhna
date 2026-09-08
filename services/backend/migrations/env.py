from alembic import context
from mozhna.db import Base, connect

target_metadata = Base.metadata

if context.is_offline_mode():
    import os
    context.configure(url=os.environ['DATABASE_URL'], target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    engine, _ = connect()
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()
