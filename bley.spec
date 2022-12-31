Name:           bley
Version:        2.0.0
Release:        1%{?dist}
Summary:        Intelligent greylisting daemon for Postfix and Exim

License:        BSD
URL:            http://bley.mx
Source0:        http://bley.mx/download/bley-%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  python3-devel
BuildRequires:  python3-setuptools

Requires:       python3-mysql
Requires:       python3-py3dns
Requires:       python3-pyspf
Requires:       python3-psycopg2
%if 0%{?fedora} > 0
Requires:       python3-publicsuffix2
%endif
Requires:       python3-twisted

Requires(post):   systemd
Requires(preun):  systemd
Requires(postun): systemd
BuildRequires:    systemd

%description
bley uses various tests (incl. RBL and SPF) to decide whether a sender should be
greylisted or not, thus mostly eliminating the usual greylisting delay while
still filtering most of the spam.


%package logcheck
Summary:  Logcheck support files for %{name}
Requires: %{name} = %{version}-%{release}
Requires: logcheck

%description logcheck
Logcheck support files for %{name}.


%prep
%setup -q


%build
%py3_build


%install
%py3_install
for file in bley.conf whitelist_clients whitelist_recipients; do
  mv $RPM_BUILD_ROOT%{_sysconfdir}/%{name}/${file}.example \
    $RPM_BUILD_ROOT%{_sysconfdir}/%{name}/${file}
done


%post
%systemd_post %{name}.service

%preun
%systemd_preun %{name}.service

%postun
%systemd_postun_with_restart %{name}.service


%files
%doc CHANGELOG.md README.md
%config(noreplace) %{_sysconfdir}/%{name}
%{_bindir}/%{name}
%{_bindir}/%{name}graph
%{python3_sitelib}/bley*
%{python3_sitelib}/postfix.py*
%{python3_sitelib}/__pycache__/*
%{_mandir}/man1/%{name}.1.gz
%{_mandir}/man1/%{name}graph.1.gz
%{_unitdir}/%{name}.service

%files logcheck
%doc CHANGELOG.md README.md
%config(noreplace) %{_sysconfdir}/logcheck/ignore.d.server/%{name}.logcheck


%changelog
* Sun Nov  9 2014 Felix Kaechele <heffer@fedoraproject.org> - 2.0.0-0
- create package spec template
