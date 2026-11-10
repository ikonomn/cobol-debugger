Name:           cobol-debugger
Version:        0.1.0
Release:        9%{?dist}
Summary:        Independent graphical debugger for GnuCOBOL
License:        0BSD AND CC-BY-4.0 AND LicenseRef-Local-Test-Only
Source0:        cobgdb-python-%{version}.tar.gz
BuildArch:      noarch
BuildRequires:  python3-devel >= 3.10
BuildRequires:  python3-qt5-base >= 5.15
BuildRequires:  desktop-file-utils
Requires:       python3 >= 3.10
Requires:       python3-qt5-base >= 5.15
Requires:       gdb
Recommends:     gnucobol
Obsoletes:      cobgdb-python < 0.1.0-7

%description
Independent Python JSON GDB/MI backend and graphical GnuCOBOL debugger.
Includes source mapping, variable inspection and flowcharts.
The GUI accepts an optional executable and original source argument.
Local test packaging includes example material whose redistribution terms need review.

%prep
%setup -q -n cobgdb-python-%{version}

%build
# Pure Python modules; RPM performs installed byte compilation.

%install
install -d %{buildroot}%{python3_sitelib}/cobgdb_python
install -pm 0644 cobgdb_python/*.py %{buildroot}%{python3_sitelib}/cobgdb_python/
install -d %{buildroot}%{python3_sitelib}/cobgdb_python/resources
install -pm 0644 cobgdb_python/resources/* %{buildroot}%{python3_sitelib}/cobgdb_python/resources/
install -Dpm 0644 cobgdb_python/resources/cobgdb.svg %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/cobol-debugger.svg
%{__python3} scripts/stage_examples.py %{buildroot}%{_docdir}/%{name}/examples
install -d %{buildroot}%{_bindir}
for entry in 'cobol-debugger-backend backend' 'cobol-debugger frontend'; do
    set -- $entry
    printf '#!%{__python3}\nfrom cobgdb_python.%s import main\nmain()\n' "$2" > %{buildroot}%{_bindir}/"$1"
    chmod 0755 %{buildroot}%{_bindir}/"$1"
done
install -d %{buildroot}%{_datadir}/applications
cat > %{buildroot}%{_datadir}/applications/cobol-debugger.desktop <<'DESKTOP'
[Desktop Entry]
Type=Application
Name=COBOL Debugger
Comment=Debug GnuCOBOL programs
Exec=cobol-debugger
Icon=cobol-debugger
Terminal=false
Categories=Development;Debugger;
StartupNotify=true
DESKTOP
chmod 0644 %{buildroot}%{_datadir}/applications/cobol-debugger.desktop
desktop-file-validate %{buildroot}%{_datadir}/applications/cobol-debugger.desktop

%check
cd %{buildroot}
PYTHONPATH=%{buildroot}%{python3_sitelib} QT_QPA_PLATFORM=offscreen %{__python3} -c 'from PyQt5 import QtCore, QtGui, QtWidgets; import cobgdb_python.frontend; import cobgdb_python.backend'
%{__python3} -m compileall -q %{buildroot}%{python3_sitelib}/cobgdb_python

%files
%license LICENSE packaging/LICENSE.local-test
%doc README.md DEVELOPMENT.md RELEASE_NOTES.md
%doc %{_docdir}/%{name}/examples
%{_datadir}/icons/hicolor/scalable/apps/cobol-debugger.svg
%{python3_sitelib}/cobgdb_python/
%{_bindir}/cobol-debugger-backend
%{_bindir}/cobol-debugger
%{_datadir}/applications/cobol-debugger.desktop

%changelog
* Mon Nov 09 2026 Local build <noreply@opencobolide.invalid> - 0.1.0-9
- Ship EU Cities and GeoNames attribution in the common examples.

* Mon Nov 09 2026 Local build <noreply@opencobolide.invalid> - 0.1.0-8
- Ship the shared GnuCOBOL / COBOL Debugger examples.

* Mon Nov 09 2026 Local Package Builder <local-build@cobol-debugger.invalid> - 0.1.0-7
- Rename the package and launchers to COBOL Debugger.

* Sat Nov 07 2026 Local build <noreply@opencobolide.invalid> - 6
- Provide writable per-user examples and preserve existing user files.

* Sat Nov 07 2026 Local Package Builder <local-build@cobol-debugger.invalid> - 0.1.0-5
- Restore the embedded program output and Linux input controls.

* Fri Nov 06 2026 Local Package Builder <local-build@cobol-debugger.invalid> - 0.1.0-4
- Include all five examples and their input data.

* Fri Nov 06 2026 Local Package Builder <local-build@cobol-debugger.invalid> - 0.1.0-3
- Add offline Help, About, installed example access and a launcher icon.

* Fri Nov 06 2026 Local Package Builder <local-build@cobol-debugger.invalid> - 0.1.0-2
- Use native program terminals and include a graphical COBOL debug example.

* Wed Nov 04 2026 Local Package Builder <local-build@cobol-debugger.invalid> - 0.1.0-1
- Initial native RPM definitions with optional executable GUI launch.
- Include interface icons, independent compiler and project bin defaults.
