Traceback (most recent call last):
  File "C:\ProgramData\Anaconda3\lib\runpy.py", line 194, in _run_module_as_main
    return _run_code(code, main_globals, None,
  File "C:\ProgramData\Anaconda3\lib\runpy.py", line 87, in _run_code
    exec(code, run_globals)
  File "C:\Users\cody.j.lepp.ctr\dev\adoctl-main\adoctl-main\adoctl\__main__.py", line 7, in <module>
    raise SystemExit(main())
  File "C:\Users\cody.j.lepp.ctr\dev\adoctl-main\adoctl-main\adoctl\cli\main.py", line 281, in main
    sync_ado_to_yaml(cfg=cfg, out_dir=args.out_dir, wit_names=args.wit, sections=sections)
  File "C:\Users\cody.j.lepp.ctr\dev\adoctl-main\adoctl-main\adoctl\sync\ado_sync.py", line 473, in sync_ado_to_yaml
    _sync_planning_semantics(
  File "C:\Users\cody.j.lepp.ctr\dev\adoctl-main\adoctl-main\adoctl\sync\ado_sync.py", line 307, in_sync_planning_semantics
    chunk_payload = ado_get(
  File "C:\Users\cody.j.lepp.ctr\dev\adoctl-main\adoctl-main\adoctl\ado_client\http.py", line 21, in ado_get
    raise RuntimeError(f"ADO GET failed ({resp.status_code}) for {url}: {body}")
RuntimeError: ADO GET failed (400) for <https://nswdevsecops.socom.mil/NSW/Black%20Lagoon/_apis/wit/workitems>: {"$id":"1","innerException":null,"message":"The expand parameter can not be used with the fields parameter.","typeName":"Microsoft.Azure.Boards.WebApi.Common.ConflictingParametersException, Microsoft.Azure.Boards.WebApi.Common","typeKey":"ConflictingParametersException","errorCode":0,"eventId":3000}
