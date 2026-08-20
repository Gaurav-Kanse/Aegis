Name:           aegis
Version:        0.1.0
Release:        1%{?dist}
Summary:        Linux system guardian and proactive resource monitor

License:        MIT
URL:            https://github.com/Gaurav-Kanse/Aegis
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  python3-devel
BuildRequires:  python3-setuptools
Requires:       python3
Requires:       python3-gobject
Requires:       gtk4
Requires:       python3-cairo

%description
Aegis is an event-driven, kernel-backed system monitor and proactive resource
daemon for Linux. It monitors RAM, CPU, disk, network, pressure, and thermal
telemetry, executing configurable desktop notifications or graceful process
recovery actions.

%prep
%autosetup -n %{name}-%{version}

%build
%py3_build

%install
%py3_install

# Install Desktop Entry
install -d %{buildroot}%{_datadir}/applications
install -m 0644 packaging/desktop/org.aegis.Aegis.desktop %{buildroot}%{_datadir}/applications/

# Install AppStream Metainfo
install -d %{buildroot}%{_datadir}/metainfo
install -m 0644 packaging/desktop/org.aegis.Aegis.metainfo.xml %{buildroot}%{_datadir}/metainfo/

# Install Scalable Icon
install -d %{buildroot}%{_datadir}/icons/hicolor/scalable/apps
install -m 0644 packaging/icons/aegis.svg %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/

# Install Systemd User Service
install -d %{buildroot}%{_userunitdir}
install -m 0644 systemd/aegis.service %{buildroot}%{_userunitdir}/

# Install Polkit Rule
install -d %{buildroot}%{_datadir}/polkit-1/rules.d
install -m 0644 polkit/99-aegis.rules %{buildroot}%{_datadir}/polkit-1/rules.d/

%files
%license LICENSE
%doc README.md
%{_bindir}/aegis
%{_bindir}/aegis-gui
%{python3_sitelib}/aegis
%{python3_sitelib}/aegis-*.egg-info
%{_datadir}/applications/org.aegis.Aegis.desktop
%{_datadir}/metainfo/org.aegis.Aegis.metainfo.xml
%{_datadir}/icons/hicolor/scalable/apps/aegis.svg
%{_userunitdir}/aegis.service
%{_datadir}/polkit-1/rules.d/99-aegis.rules

%changelog
* Thu Aug 20 2026 Gaurav <gauravkanse27@gmail.com> - 0.1.0-1
- Initial release of Aegis 0.1.0 for Fedora
