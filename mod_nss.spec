%{!?_httpd_apxs:       %{expand: %%global _httpd_apxs       %%{_sbindir}/apxs}}
%{!?_httpd_confdir:    %{expand: %%global _httpd_confdir    %%{_sysconfdir}/httpd/conf.d}}
%{!?_httpd_mmn: %{expand: %%global _httpd_mmn %%(cat %{_includedir}/httpd/.mmn 2>/dev/null || echo 0-0)}}

Name: mod_nss
Version: 1.0.10
Release: 1%{?dist}
Summary: SSL/TLS module for the Apache HTTP server
Group: System Environment/Daemons
License: ASL 2.0
URL: https://fedorahosted.org/mod_nss/
Source: http://fedorahosted.org/released/mod_nss/%{name}-%{version}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildRequires: nspr-devel >= 4.10.2, nss-devel >= 3.15.0.0
BuildRequires: httpd-devel >= 2.2.15-24, apr-devel, apr-util-devel
BuildRequires: pkgconfig
BuildRequires: autoconf
BuildRequires: automake
BuildRequires: libtool
Requires: httpd-mmn = %{_httpd_mmn}
Requires(post): httpd, nss-tools
Requires: nss%{?_isa} >= 3.15.0.0
# When the system 'nss' was bumped to version 3.15, an error was
# exposed in 'nss-softokn'.  Consequently, since we needed to
# increment the 'nss' dependency to coincide with the system
# 'nss', we were also forced to explicitly require the minimum
# version of 'nss-softokn' which fixed the issue exposed by
# version 3.15 of 'nss' as reported in 'Bugzilla Bug #105437 -
# Admin server segfault when configuration DS configured on
# SSL port'.
Requires: nss-softokn >= 3.14.3-11
# Although the following change reverses the desire of Bugzilla Bug #601939, it
# was provided to suppress the dangling symlink warning of Bugzilla Bug #906089
# as exposed via 'rpmlint'.
Requires: %{_libdir}/libnssckbi.so

# Change configuration to not conflict with mod_ssl
Patch1: mod_nss-conf.patch
# Generate a password-less NSS database
Patch2: mod_nss-gencert.patch
# Downgrade 'httpd 2.4' to 'httpd 2.2'
Patch3: mod_nss-downgrade_httpd_2.4_to_httpd_2.2.patch

%description
The mod_nss module provides strong cryptography for the Apache Web
server via the Secure Sockets Layer (SSL) and Transport Layer
Security (TLS) protocols using the Network Security Services (NSS)
security library.

%prep
%setup -q
%patch1 -p1 -b .conf
%patch2 -p1 -b .gencert
%patch3 -p1 -b .downgrade_httpd_2.4_to_httpd_2.2

# Touch expression parser sources to prevent regenerating it
touch nss_expr_*.[chyl]

%build

CFLAGS="$RPM_OPT_FLAGS"
APXS=%{_httpd_apxs}

export CFLAGS APXS

NSPR_INCLUDE_DIR=`/usr/bin/pkg-config --variable=includedir nspr`
NSPR_LIB_DIR=`/usr/bin/pkg-config --variable=libdir nspr`

NSS_INCLUDE_DIR=`/usr/bin/pkg-config --variable=includedir nss`
NSS_LIB_DIR=`/usr/bin/pkg-config --variable=libdir nss`

NSS_BIN=`/usr/bin/pkg-config --variable=exec_prefix nss`

autoreconf -i -f
%configure \
    --with-nss-lib=$NSS_LIB_DIR \
    --with-nss-inc=$NSS_INCLUDE_DIR \
    --with-nspr-lib=$NSPR_LIB_DIR \
    --with-nspr-inc=$NSPR_INCLUDE_DIR \
    --with-apr-config --enable-ecc

make %{?_smp_mflags} all

%install
# The install target of the Makefile isn't used because that uses apxs
# which tries to enable the module in the build host httpd instead of in
# the build root.
rm -rf $RPM_BUILD_ROOT

mkdir -p $RPM_BUILD_ROOT%{_sysconfdir}/httpd/conf
mkdir -p $RPM_BUILD_ROOT%{_httpd_confdir}
mkdir -p $RPM_BUILD_ROOT%{_libdir}/httpd/modules
mkdir -p $RPM_BUILD_ROOT%{_libexecdir}
mkdir -p $RPM_BUILD_ROOT%{_sbindir}
mkdir -p $RPM_BUILD_ROOT%{_sysconfdir}/httpd/alias
mkdir -p $RPM_BUILD_ROOT%{_mandir}/man8

install -m 644 gencert.8 $RPM_BUILD_ROOT%{_mandir}/man8/
install -m 644 nss_pcache.8 $RPM_BUILD_ROOT%{_mandir}/man8/

install -m 644 nss.conf $RPM_BUILD_ROOT%{_httpd_confdir}

install -m 755 .libs/libmodnss.so $RPM_BUILD_ROOT%{_libdir}/httpd/modules/
install -m 755 nss_pcache $RPM_BUILD_ROOT%{_libexecdir}/
# Provide a compatibility link to prevent disruption of customized deployments.
#
#     NOTE:  This link may be deprecated in a future release of 'mod_nss'.
#
ln -s %{_libexecdir}/nss_pcache $RPM_BUILD_ROOT%{_sbindir}/nss_pcache
install -m 755 gencert $RPM_BUILD_ROOT%{_sbindir}/
ln -s ../../../%{_libdir}/libnssckbi.so $RPM_BUILD_ROOT%{_sysconfdir}/httpd/alias/
touch $RPM_BUILD_ROOT%{_sysconfdir}/httpd/alias/secmod.db
touch $RPM_BUILD_ROOT%{_sysconfdir}/httpd/alias/cert8.db
touch $RPM_BUILD_ROOT%{_sysconfdir}/httpd/alias/key3.db
touch $RPM_BUILD_ROOT%{_sysconfdir}/httpd/alias/install.log

perl -pi -e "s:$NSS_LIB_DIR:$NSS_BIN:" $RPM_BUILD_ROOT%{_sbindir}/gencert

%clean
rm -rf $RPM_BUILD_ROOT

%post
umask 077

if [ "$1" -eq 1 ] ; then
    if [ ! -e %{_sysconfdir}/httpd/alias/key3.db ]; then
        %{_sbindir}/gencert %{_sysconfdir}/httpd/alias > %{_sysconfdir}/httpd/alias/install.log 2>&1
    fi

    # Make sure that the database ownership is setup properly.
    /bin/find %{_sysconfdir}/httpd/alias -user root -name "*.db" -exec /bin/chgrp apache {} \;
    /bin/find %{_sysconfdir}/httpd/alias -user root -name "*.db" -exec /bin/chmod g+r {} \;
fi

%files
%defattr(-,root,root,-)
%doc README LICENSE docs/mod_nss.html
%{_mandir}/man8/*
%config(noreplace) %{_httpd_confdir}/nss.conf
%{_libdir}/httpd/modules/libmodnss.so
%dir %{_sysconfdir}/httpd/alias/
%ghost %attr(0640,root,apache) %config(noreplace) %{_sysconfdir}/httpd/alias/secmod.db
%ghost %attr(0640,root,apache) %config(noreplace) %{_sysconfdir}/httpd/alias/cert8.db
%ghost %attr(0640,root,apache) %config(noreplace) %{_sysconfdir}/httpd/alias/key3.db
%ghost %config(noreplace) %{_sysconfdir}/httpd/alias/install.log
%{_sysconfdir}/httpd/alias/libnssckbi.so
%{_libexecdir}/nss_pcache
%{_sbindir}/nss_pcache
%{_sbindir}/gencert

%changelog
* Thu Jan 22 2015 Matthew Harmsen <mharmsen@redhat.com> - 1.0.10-1
- Resolves: rhbz #1166316 - Rebase mod_nss to 1.0.10 to support TLSv1.2

* Thu Jun  5 2014 Matthew Harmsen <mharmsen@redhat.com> - 1.0.8-21
- Bumped version build/runtime requirements for 'nspr' and 'nss'
- Added runtime dependency for 'nss-softokn'
- Bugzilla Bug #1002733 - Apache core generated with sig 5
- Bugzilla Bug #1016628 - mod_nss httpd segfaulting regularly
- Bugzilla Bug #866703 - Memory error in mod_nss (eol_memmove.patch)

* Wed Nov 27 2013 Rob Crittenden <rcritten@redhat.com> - 1.0.8-20
- Resolves: CVE-2013-4566
- Bugzilla Bug #1030267 - mod_nss: incorrect handling of NSSVerifyClient in
  directory context [rhel-6.6]

* Fri Nov 15 2013 Rob Crittenden <rcritten@redhat.com> - 1.0.8-19
- Resolves: CVE-2013-4566
- Bugzilla Bug #1030265 - mod_nss: incorrect handling of NSSVerifyClient in
  directory context [rhel-6.5.z]

* Tue Oct 23 2012 Matthew Harmsen <mharmsen@redhat.com> - 1.0.8-18
- Fixes Bugzilla Bug #835071 - [RFE] Support ability to share mod_proxy with
  other SSL providers (w/jorton, nkinder, & rcritten)

* Tue Oct 16 2012 Matthew Harmsen <mharmsen@redhat.com> - 1.0.8-17
- Fixes Bugzilla Bug #816394 - [RFE] Provide Apache 2.2 support for TLS v1.1
  via NSS through mod_nss . . .
- Bumped version build/runtime requirements for NSPR and NSS

* Wed Oct 03 2012 Matthew Harmsen <mharmsen@redhat.com> - 1.0.8-16
- Fixes Bugzilla Bug #769906 - mod_nss insists on Required value
  NSSCipherSuite not set. (mod_nss-proxyvariables.patch)

* Wed Feb 29 2012 Rob Crittenden <rcritten@redhat.com> - 1.0.8-15
- Fixes Bugzilla Bug #749408 - PK11_ListCerts called to retrieve all user
  certificates for every server (mod_nss-PK11_ListCerts.patch)
- Fixes Bugzilla Bug #749409 - Add '--enable-ecc' option to %%configure
  line under %%build section of RHEL 6 spec file

* Wed Feb 29 2012 Robert Relyea <rrelyea@redhat.com> - 1.0.8-14
- Fix 'Bugzilla Bug #797358 - mod_nss fails debug assertion' by removing
  'mod_nss-no_shutdown_if_not_init.patch' and applying
  'mod_nss-no_shutdown_if_not_init_2.patch' instead
- The 'mod_nss-no_shutdown_if_not_init_2.patch' patch also fixes
  Bugzilla Bug #797326 - File descriptor leak after "service httpd reload"
  or httpd doesn't reload

* Mon Aug  1 2011 Rob Crittenden <rcritten@redhat.com> - 1.0.8-13
- Fix array overrun when launching nss_pcache (#714154)
- For FakeBasicAuth retrieve the entire subject, not just CN. Prefix this
  with "/" to be compatible with OpenSSL.
  Always retrieve the client certificate, not just on the first request
  it is needed. (#702437)
- Don't try to shut down NSS if it wasn't initialized. (#691502)

* Wed Mar  9 2011 Rob Crittenden <rcritten@redhat.com> - 1.0.8-12
- Use memmove in place of memcpy since the buffers can overlap (#682326)

* Wed Mar  2 2011 Rob Crittenden <rcritten@redhat.com> - 1.0.8-11
- Lock around the pipe to nss_pcache for retrieving the token PIN
  (#677700)

* Mon Feb  2 2011 Rob Crittenden <rcritten@redhat.com> - 1.0.8-10
- Apply the patch for #634687

* Mon Feb  2 2011 Rob Crittenden <rcritten@redhat.com> - 1.0.8-9
- Add man page for gencert (#605376)
- Fix hang when handling large POST under some conditions (#634687)

* Mon Jun 14 2010 Rob Crittenden <rcritten@redhat.com> - 1.0.8-8
- Add Requires on nss-tools for default db creation (#603172)

* Thu May 20 2010 Rob Crittenden <rcritten@redhat.com> - 1.0.8-7
- Use remote hostname set by mod_proxy to compare to CN in peer cert (#591901)

* Thu Mar 18 2010 Rob Crittenden <rcritten@redhat.com> - 1.0.8-6
- Patch to add configuration options for new NSS negotiation API (#574187)
- Set minimum version of nss to 3.12.6 to pick up renegotiation fix

* Wed Feb 24 2010 Rob Crittenden <rcritten@redhat.com> - 1.0.8-5
- Add (pre) for Requires on httpd so we can be sure the user and group are
  already available
- Add file Requires on libnssckbi.so so symlink can't fail
- Use _sysconfdir macro instead of /etc

* Tue Feb 23 2010 Rob Crittenden <rcritten@redhat.com> - 1.0.8-4
- Remove unused variable and perl substitution for gencert. gencert used to
  have separate variables for NSS & NSPR libraries, that is gone now so this
  variable and substitution aren't needed.
- Added comments to patch to identify what they do

* Wed Jan 27 2010 Rob Crittenden <rcritten@redhat.com> - 1.0.8-3
- The location of libnssckbi.so moved from /lib[64] to /usr/lib[64] (#558545)
- Don't generate output when the default NSS database is generated (#538859)

* Mon Nov 30 2009 Dennis Gregorovic <dgregor@redhat.com> - 1.0.8-2.1
- Rebuilt for RHEL 6

* Sat Jul 25 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.0.8-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_12_Mass_Rebuild

* Mon Mar  2 2009 Rob Crittenden <rcritten@redhat.com> - 1.0.8-1
- Update to 1.0.8
- Add patch that fixes NSPR layer bug

* Wed Feb 25 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.0.7-11
- Rebuilt for https://fedoraproject.org/wiki/Fedora_11_Mass_Rebuild

* Mon Aug 11 2008 Tom "spot" Callaway <tcallawa@redhat.com> - 1.0.7-10
- fix license tag

* Mon Jul 28 2008 Rob Crittenden <rcritten@redhat.com> - 1.0.7-9
- rebuild to bump NVR

* Mon Jul 14 2008 Rob Crittenden <rcritten@redhat.com> - 1.0.7-8
- Don't force module de-init during the configuration stage (453508)

* Thu Jul 10 2008 Rob Crittenden <rcritten@redhat.com> - 1.0.7-7
- Don't inherit the MP cache in multi-threaded mode (454701)
- Don't initialize NSS in each child if SSL isn't configured

* Wed Jul  2 2008 Rob Crittenden <rcritten@redhat.com> - 1.0.7-6
- Update the patch for FIPS to include fixes for nss_pcache, enforce
  the security policy and properly initialize the FIPS token.

* Mon Jun 30 2008 Rob Crittenden <rcritten@redhat.com> - 1.0.7-5
- Include patch to fix NSSFIPS (446851)

* Mon Apr 28 2008 Rob Crittenden <rcritten@redhat.com> - 1.0.7-4
- Apply patch so that mod_nss calls NSS_Init() after Apache forks a child
  and not before. This is in response to a change in the NSS softtokn code
  and should have always been done this way. (444348)
- The location of libnssckbi moved from /usr/lib[64] to /lib[64]
- The NSS database needs to be readable by apache since we need to use it
  after the root priviledges are dropped.

* Tue Feb 19 2008 Fedora Release Engineering <rel-eng@fedoraproject.org> - 1.0.7-3
- Autorebuild for GCC 4.3

* Thu Oct 18 2007 Rob Crittenden <rcritten@redhat.com> 1.0.7-2
- Register functions needed by mod_proxy if mod_ssl is not loaded.

* Fri Jun  1 2007 Rob Crittenden <rcritten@redhat.com> 1.0.7-1
- Update to 1.0.7
- Remove Requires for nss and nspr since those are handled automatically
  by versioned libraries
- Updated URL and Source to reference directory.fedoraproject.org

* Mon Apr  9 2007 Rob Crittenden <rcritten@redhat.com> 1.0.6-2
- Patch to properly detect the Apache model and set up NSS appropriately
- Patch to punt if a bad password is encountered
- Patch to fix crash when password.conf is malformatted
- Don't enable ECC support as NSS doesn't have it enabled (3.11.4-0.7)

* Mon Oct 23 2006 Rob Crittenden <rcritten@redhat.com> 1.0.6-1
- Update to 1.0.6

* Fri Aug 04 2006 Rob Crittenden <rcritten@redhat.com> 1.0.3-4
- Include LogLevel warn in nss.conf and use separate log files

* Fri Aug 04 2006 Rob Crittenden <rcritten@redhat.com> 1.0.3-3
- Need to initialize ECC certificate and key variables

* Fri Aug 04 2006 Jarod Wilson <jwilson@redhat.com> 1.0.3-2
- Use %%ghost for db files and install.log

* Tue Jun 20 2006 Rob Crittenden <rcritten@redhat.com> 1.0.3-1
- Initial build
