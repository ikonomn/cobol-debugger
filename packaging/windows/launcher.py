"""Windows one-file application and its protocol/build workers."""
import sys

if sys.argv[1:2] == ['--cobgdb-backend']:
    from cobgdb_python.backend import main
    main()
elif sys.argv[1:2] == ['--cobgdb-build']:
    from cobgdb_python.project_build import main
    del sys.argv[1]
    raise SystemExit(main())
else:
    from cobgdb_python.frontend import main
    main()
