Name:           cobgdb-python
Version:        0.1.0
Release:        5%{?dist}
Summary:        Independent graphical debugger for GnuCOBOL
License:        LicenseRef-Local-Test-Only
Source0:        %{name}-%{version}.tar.gz
Group:          Development/Other
BuildArch:      noarch
BuildRequires:  python3-devel >= 3.10
BuildRequires:  python3-qt5-gui >= 5.15
BuildRequires:  python3-rpm-macros
BuildRequires:  desktop-file-utils
Requires:       python3 >= 3.10
Requires:       python3-qt5-gui >= 5.15
Requires:       gdb
Recommends:     gnucobol

%description
Independent Python JSON GDB/MI backend and graphical GnuCOBOL debugger.
Includes project builds, source mapping, variable inspection and flowcharts.
The GUI accepts an optional executable and original source argument.
Local test packaging: upstream redistribution license has not been specified.

%prep
%setup -q

%build
# Pure Python modules; RPM performs installed byte compilation.

%install
install -d %{buildroot}%{python3_sitelib}/cobgdb_python
install -pm 0644 cobgdb_python/*.py %{buildroot}%{python3_sitelib}/cobgdb_python/
install -d %{buildroot}%{python3_sitelib}/cobgdb_python/resources
install -pm 0644 cobgdb_python/resources/* %{buildroot}%{python3_sitelib}/cobgdb_python/resources/
install -Dpm 0644 cobgdb_python/resources/cobgdb.svg %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/cobgdb-python.svg
%{__python3} scripts/stage_examples.py %{buildroot}%{_docdir}/%{name}/examples
install -d %{buildroot}%{_bindir}
for entry in 'cobgdb-python backend' 'cobgdb-python-gui frontend'; do
    set -- $entry
    printf '#!%{__python3}\nfrom cobgdb_python.%s import main\nmain()\n' "$2" > %{buildroot}%{_bindir}/"$1"
    chmod 0755 %{buildroot}%{_bindir}/"$1"
done
install -d %{buildroot}%{_datadir}/applications
cat > %{buildroot}%{_datadir}/applications/cobgdb-python.desktop <<'DESKTOP'
[Desktop Entry]
Type=Application
Name=COBGDB Python Debugger
Comment=Debug GnuCOBOL programs
Exec=cobgdb-python-gui
Icon=cobgdb-python
Terminal=false
Categories=Development;Debugger;
StartupNotify=true
DESKTOP
chmod 0644 %{buildroot}%{_datadir}/applications/cobgdb-python.desktop
desktop-file-validate %{buildroot}%{_datadir}/applications/cobgdb-python.desktop

%check
cd %{buildroot}
PYTHONPATH=%{buildroot}%{python3_sitelib} QT_QPA_PLATFORM=offscreen %{__python3} -c 'from PyQt5 import QtCore, QtGui, QtWidgets; import cobgdb_python.frontend; import cobgdb_python.backend'
%{__python3} -m compileall -q %{buildroot}%{python3_sitelib}/cobgdb_python

%files
%license packaging/LICENSE.local-test
%doc README.md DEVELOPMENT.md RELEASE_NOTES.md
%doc %{_docdir}/%{name}/examples
%{_datadir}/icons/hicolor/scalable/apps/cobgdb-python.svg
%{python3_sitelib}/cobgdb_python/
%{_bindir}/cobgdb-python
%{_bindir}/cobgdb-python-gui
%{_datadir}/applications/cobgdb-python.desktop

%changelog
* Sat Nov 07 2026 Local Package Builder <local-build@cobgdb-python.invalid> - 0.1.0-5
- Restore the embedded program output and Linux input controls.

* Fri Nov 06 2026 Local Package Builder <local-build@cobgdb-python.invalid> - 0.1.0-4
- Include all five examples and their input data.

* Fri Nov 06 2026 Local Package Builder <local-build@cobgdb-python.invalid> - 0.1.0-3
- Add offline Help, About, installed example access and a launcher icon.

* Fri Nov 06 2026 Local Package Builder <local-build@cobgdb-python.invalid> - 0.1.0-2
- Use native program terminals and include a graphical COBOL debug example.

* Wed Nov 04 2026 Local Package Builder <local-build@cobgdb-python.invalid> - 0.1.0-1
- Initial native RPM definitions with optional executable GUI launch.
- Include interface icons, independent compiler and project bin defaults.
