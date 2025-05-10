```
async with async_engine.connect() as conn:
    inspector_result = await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_pk_constraint("auth_users"))
    print(inspector_result)
```