%{!?_httpd_apxs:       %{expand: %%global _httpd_apxs       %%{_sbindir}/apxs}}
%{!?_httpd_confdir:    %{expand: %%global _httpd_confdir    %%{_sysconfdir}/httpd/conf.d}}
# /etc/httpd/conf.d with httpd < 2.4 and defined as /etc/httpd/conf.modules.d with httpd >= 2.4
%{!?_httpd_modconfdir: %{expand: %%global _httpd_modconfdir %%{_sysconfdir}/httpd/conf.d}}
%{!?_httpd_mmn: %{expand: %%global _httpd_mmn %%(cat %{_includedir}/httpd/.mmn 2>/dev/null || echo 0-0)}}

Name: mod_nss
Version: 1.0.14
Release: 10%{?dist}
Summary: SSL/TLS module for the Apache HTTP server
Group: System Environment/Daemons
License: ASL 2.0
URL: https://fedorahosted.org/mod_nss/
Source: http://fedorahosted.org/released/mod_nss/%{name}-%{version}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildRequires: nspr-devel >= 4.10.8, nss-devel >= 3.19.1
BuildRequires: httpd-devel, apr-devel, apr-util-devel
BuildRequires: pkgconfig
BuildRequires: autoconf
BuildRequires: automake
BuildRequires: libtool
# Needed for make check
BuildRequires: openssl
BuildRequires: python-nose
BuildRequires: python-requests
BuildRequires: python-urllib3
Requires: httpd-mmn = %{_httpd_mmn}
Requires(post): httpd, nss-tools
Requires: nss%{?_isa} >= 3.19.1
# Although the following change reverses the desire of Bugzilla Bug #601939, it
# was provided to suppress the dangling symlink warning of Bugzilla Bug #906089
# as exposed via 'rpmlint'.
Requires: %{_libdir}/libnssckbi.so

# Change configuration to not conflict with mod_ssl
Patch1: mod_nss-conf.patch
# Generate a password-less NSS database
Patch2: mod_nss-gencert.patch
# Set DEFAULT_SSL_CIPHER_LIST manually if pyopenssl can't be imported
Patch3: mod_nss-defaultcipherlist.patch
# Match the available ciphers in RHEL OpenSSL so tests pass
Patch4: mod_nss-test-cipherlist.patch 
# Disable and fix tests to work inside of brew
Patch5: mod_nss-brewtest.patch
# Remove setting 'r->user' in nss_hook_Fixup()
Patch6: mod_nss-remove-r-user-from-hook-fixup.patch
# Cleanup nss_pcache semaphore on shutdown
Patch7: mod_nss-clean-semaphore.patch
# Check certificate database directory permissions
Patch8: mod_nss-certdb-permissions.patch
# Die on invalid Protocol settings
Patch9: mod_nss-invalid-protocol-setting.patch
# Handle group membership when testing file perms
Patch10: mod_nss-group-permissions.patch
# Add OCSP cache tuning directives
Patch11: mod_nss-ocsp-tuning-knobs.patch
# Use NoDBInit in nss_pcache
Patch12: mod_nss-pcache_nodbinit.patch
# Update nss_pcache man page to drop directory and prefix
Patch13: mod_nss-nss_pcache_man.patch

%description
The mod_nss module provides strong cryptography for the Apache Web
server via the Secure Sockets Layer (SSL) and Transport Layer
Security (TLS) protocols using the Network Security Services (NSS)
security library.

%prep
%setup -q
%patch1 -p1 -b .conf
%patch2 -p1 -b .gencert
%patch3 -p1 -b .defaultcipherlist
%patch4 -p1 -b .testcipherlist
%patch5 -p1 -b .brewtest
%patch6 -p1 -b .remove_r_user
%patch7 -p1 -b .semaphore
%patch8 -p1 -b .permissions
%patch9 -p1 -b .protocol_fatal
%patch10 -p1 -b .group_permissions
%patch11 -p1 -b .ocsp_tuning
%patch12 -p1 -b .pcache_nodbinit
%patch13 -p1 -b .pcache_man

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

%if "%{_httpd_modconfdir}" != "%{_httpd_confdir}"
# httpd >= 2.4.x
mkdir -p $RPM_BUILD_ROOT%{_httpd_modconfdir}
sed -n /^LoadModule/p nss.conf > 10-nss.conf
sed -i /^LoadModule/d nss.conf
install -m 644 10-nss.conf $RPM_BUILD_ROOT%{_httpd_modconfdir}
%endif

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
ln -s %{_libdir}/libnssckbi.so $RPM_BUILD_ROOT%{_sysconfdir}/httpd/alias/
touch $RPM_BUILD_ROOT%{_sysconfdir}/httpd/alias/secmod.db
touch $RPM_BUILD_ROOT%{_sysconfdir}/httpd/alias/cert8.db
touch $RPM_BUILD_ROOT%{_sysconfdir}/httpd/alias/key3.db
touch $RPM_BUILD_ROOT%{_sysconfdir}/httpd/alias/install.log

perl -pi -e "s:$NSS_LIB_DIR:$NSS_BIN:" $RPM_BUILD_ROOT%{_sbindir}/gencert

%check
make check

%clean
rm -rf $RPM_BUILD_ROOT

%post
umask 077

if [ "$1" -eq 1 ] ; then
    if [ ! -e %{_sysconfdir}/httpd/alias/key3.db ]; then
        %{_sbindir}/gencert %{_sysconfdir}/httpd/alias > %{_sysconfdir}/httpd/alias/install.log 2>&1
        echo ""
        echo "%{name} certificate database generated."
        echo ""
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
%if "%{_httpd_modconfdir}" != "%{_httpd_confdir}"
%config(noreplace) %{_httpd_modconfdir}/10-nss.conf
%endif
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
* Wed May 10 2017 Rob Crittenden <rcritten@redhat.com> - 1.0.14-10
- Apply the nss_pcache man page patch (#1382102)

* Wed May 10 2017 Rob Crittenden <rcritten@redhat.com> - 1.0.14-9
- Update nss_pcache.8 to drop directory and prefix options (#1382102)

- Don't share mod_nss NSS database with nss_pcache (#1382102)
* Thu Feb 23 2017 Rob Crittenden <rcritten@redhat.com> - 1.0.14-8
- Fail start start when there are invalid Protocols defined (#1389114)
- Handle group membership when testing NSS database filesystem
  permissions (#1395300)
- Add OCSP cache tuning directives (#1392582) 
- Don't share mod_nss NSS database with nss_pcache (#1382102)

* Wed Sep 21 2016 Rob Crittenden <rcritten@redhat.com> - 1.0.14-7
- Add the permission patch to the repository (#1312583)

* Wed Sep 21 2016 Rob Crittenden <rcritten@redhat.com> - 1.0.14-6
- Check the NSS certificate database directory for read permissions
  by the Apache user. (#1312583)

* Wed Aug 10 2016 Rob Crittenden <rcritten@redhat.com> - 1.0.14-5
- Update clean semaphore patch to not free the pinList twice.
  (#1364560)

* Tue Aug  9 2016 Rob Crittenden <rcritten@redhat.com> - 1.0.14-4
- Update clean semaphore patch to not close pipe twice and to
  shutdown NSS database (#1364560)

* Mon Aug  8 2016 Rob Crittenden <rcritten@redhat.com> - 1.0.14-3
- Clean up semaphore in nss_pcache on shutdown (#1364560)

* Tue Jun 28 2016 Matthew Harmsen <mharmsen@redhat.com> - 1.0.14-2
- mod_nss sets r->user in fixup even if it was long ago changed
  by other module (#1347298)

* Mon May 23 2016 Rob Crittenden <rcritten@redhat.com> - 1.0.14-1
- Rebase to 1.0.14 (#1299063)
- Add support for Server Name Indication (SNI) (#1053327)
- Use upstream method to not execute live tests as root (#1256887)
- Always call SSL_ShutdownServerSessionIDCache() in ModuleKill
  (#1263301, #1296685)
- Don't require NSSProxyNickname (#1280287)
- Make link to libnssckbi.so an absolute link (#1288471)
- Fail for colons in credentials with FakeBasicAuth (#1295970)
- Don't ignore NSSProtocol when NSSFIPS is enabled (#1312491)
- Check filesystem permissions on NSS database at startup (#1312583)
- OpenSSL ciphers stopped parsing at +, CVE-2016-3099 (#1323913)
- Patch to match available ciphers so tests pass (#1299063)
- Patch to fix tests in brew (#1299063)

* Tue Sep 22 2015 Rob Crittenden <rcritten@redhat.com> - 1.0.11-6
- Add the supported NSS SHA384 ciphers (#1253570)
- Add kECDH, AECDH, ECDSA and aECDSA macros (#1253570)
- Bump the NSS BR and Requires so the new ciphers are available
- Bump the NSPR Requires to match NSS

* Mon Sep 21 2015 Rob Crittenden <rcritten@redhat.com> - 1.0.11-5
- Don't enable NULL ciphers in DEFAULT macro (#1253570)
- Add OpenSSL cipher macro EECDH (#1160745)
- Disable the live server testing in make check because it
  may run as root and fail horribly (#1160745)

* Thu Aug 27 2015 Rob Crittenden <rcritten@redhat.com> - 1.0.11-4
- Handle permanently disabled ciphers in call to SSL_CipherPrefSet
  (#1160745)

* Mon Aug 17 2015 Rob Crittenden <rcritten@redhat.com> - 1.0.11-3
- Fix logical and support in cipher strings CVE-2015-3277
  (#1253570)
- Add missing BuildRequires and small patch to use requests.urllib3
  to fix make check (#1253570)

* Wed Jul 29 2015 Matthew Harmsen <mharmsen@redhat.com> - 1.0.11-2
- Resolves: rhbz #1066236
- Bugzilla Bug #1066236 - mod_nss: documentation formatting fixes

* Thu Jun 11 2015 Rob Crittenden <rcritten@redhat.com> - 1.0.11-1
- Resolves: rhbz #1160745 - Rebase mod_nss to 1.0.11

* Mon Jan  5 2015 Matthew Harmsen <mharmsen@redhat.com> - 1.0.8-33
- Resolves: rhbz #1169871
- Bugzilla Bug #1169871 -  Default configuration enables SSL3

* Fri Jan 24 2014 Daniel Mach <dmach@redhat.com> - 1.0.8-32
- Mass rebuild 2014-01-24

* Mon Jan 13 2014 Matthew Harmsen <mharmsen@redhat.com> - 1.0.8-31
- Resolves: rhbz #1029360
- Bugzilla Bug #1029360 - ambiguous/invalid ENVR in httpd-mmn Provides/Requires
- corrected typo on date

* Mon Jan 13 2014 Matthew Harmsen <mharmsen@redhat.com> - 1.0.8-30
- Resolves: rhbz #1029360
- Bugzilla Bug #1029360 - ambiguous/invalid ENVR in httpd-mmn Provides/Requires

* Fri Dec 27 2013 Daniel Mach <dmach@redhat.com> - 1.0.8-29
- Mass rebuild 2013-12-27

* Wed Nov 27 2013 Matthew Harmsen <mharmsen@redhat.com> - 1.0.8-28
- Resolves: rhbz #1030276
- [mod_nss-usecases.patch]
- Bugzilla Bug #1030276 - mod_nss not working in FIPS mode

* Fri Nov 15 2013 Rob Crittenden <rcritten@redhat.com> - 1.0.8-27
- Resolves: CVE-2013-4566
- Bugzilla Bug #1024536 - mod_nss: incorrect handling of NSSVerifyClient in
  directory context [rhel-7.0] (rcritten)
- Bugzilla Bug #1030845 - mod_nss: do not use %%configure in %%changelog
  (mharmsen)

* Tue Nov 12 2013 Joe Orton <jorton@redhat.com> - 1.0.8-26
- [mod_nss-SSLEngine-off.patch]
- Bugzilla Bug #1029042 - Implicit SSLEngine for 443 port breaks mod_nss
  configuration (jorton)
- [mod_nss-unused-filter_ctx.patch]
- Bugzilla Bug #1029665 - Remove unused variable 'filter_ctx' (mharmsen)

* Fri Nov  1 2013 Tomas Hoger <thoger@redhat.com> - 1.0.8-25
- Bugzilla Bug #1025317 - mod_nss: documentation formatting fixes [rhel-7]

* Thu Oct 24 2013 Matthew Harmsen <mharmsen@redhat.com> - 1.0.8-24
- Add '--enable-ecc' option to %%configure line under %%build section of
  this spec file (mharmsen)
- Bumped version build/runtime requirements for NSPR and NSS (mharmsen)
- [mod_nss-PK11_ListCerts_2.patch]
- Bugzilla Bug #1022295 - PK11_ListCerts called to retrieve all user
  certificates for every server (rcritten)
- [mod_nss-array_overrun.patch]
- Bugzilla Bug #1022298 - overrunning array when executing nss_pcache
  (rcritten)
- [mod_nss-clientauth.patch]
- Bugzilla Bug #1022921 - mod_nss: FakeBasicAuth authentication bypass
  [rhel-7.0] (rcritten)
- [mod_nss-no_shutdown_if_not_init_2.patch]
- Bugzilla Bug #1022303 - File descriptor leak after "service httpd reload"
  or httpd doesn't reload (rrelyea)
- [mod_nss-proxyvariables.patch]
- Bugzilla Bug #1022309 - mod_nss insists on Required value NSSCipherSuite
  not set. (mharmsen)
- [mod_nss-tlsv1_1.patch]
- Bugzilla Bug #1022310 - current nss support TLS 1.1 so mod_nss should pick
  it up (mharmsen)
- [mod_nss-sslmultiproxy_2.patch]
- Fixes Bugzilla Bug #1021458 - [RFE] Support ability to share mod_proxy with
  other SSL providers (jorton, mharmsen, nkinder, & rcritten)

* Tue Jul 30 2013 Joe Orton <jorton@redhat.com> - 1.0.8-23
- add dependency on httpd-mmn

* Wed Jul  3 2013 Matthew Harmsen <mharmsen@redhat.com> - 1.0.8-22
- Moved 'nss_pcache' from %%sbindir to %%libexecdir
  (provided compatibility link)

* Tue Jul  2 2013 Matthew Harmsen <mharmsen@redhat.com> - 1.0.8-21.1
- Add the following explanation to the 'Dangling symlinks' textbox in rpmdiff:
  Symlink 'etc/httpd/alias/libnssckbi.so' is deliberate.
  This test does not belong in rpmdiff. This test belongs in TPS.
  Since the symlink points to a file in another package, e.g. a
  dependency or a system file, rpmdiff cannot detect this. Remember,
  rpmdiff does not install or even know about package dependencies.
  That's TPS's job.
- Add the following explanation to the 'Brewtap results' textbox in rpmdiff:
  The '/etc/httpd/conf.d/nss.conf' file does not require a man page
  because its parameters are sufficiently documented within the
  configuration file itself.
  The '/etc/httpd/conf.modules.d/10-nss.conf' file does not require
  a man page because the file merely contains the line
  'LoadModule nss_module modules/libmodnss.so' to support httpd
  loading of Dynamic Shared Objects ('/etc/httpd/conf/httpd.conf').

* Tue Jun 25 2013 Matthew Harmsen <mharmsen@redhat.com> - 1.0.8-21
- Bugzilla Bug #884115 - Package mod_nss-1.0.8-18.1.el7 failed RHEL7 RPMdiff
  testing
- Bugzilla Bug #906082 - mod_nss requires manpages for gencert and nss_pcache
- Bugzilla Bug #906089 - Fix dangling symlinks in mod_nss
- Bugzilla Bug #906097 - Correct RPM Parse Warning in mod_nss.spec
- Bugzilla Bug #948601 - Man page scan results for mod_nss

* Thu Feb 14 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.0.8-20.1
- Rebuilt for https://fedoraproject.org/wiki/Fedora_19_Mass_Rebuild

* Fri Jul 20 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.0.8-19.1
- Rebuilt for https://fedoraproject.org/wiki/Fedora_18_Mass_Rebuild

* Mon Jun 18 2012 Joe Orton <jorton@redhat.com> - 1.0.8-18.1
- fix build for RHEL7

* Fri Jun 15 2012 Rob Crittenden <rcritten@redhat.com> - 1.0.8-18
- Actually apply the patch to use memmove in place of memcpy since the
  buffers can overlap (#669118)

* Tue Jun 12 2012 Nathan Kinder <nkinder@redhat.com> - 1.0.8-17
- Port mod_nss to work with httpd 2.4

* Mon Apr 23 2012 Joe Orton <jorton@redhat.com> - 1.0.8-16
- packaging fixes/updates (#803072)

* Fri Jan 13 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.0.8-15
- Rebuilt for https://fedoraproject.org/wiki/Fedora_17_Mass_Rebuild

* Mon Mar  7 2011 Rob Crittenden <rcritten@redhat.com> - 1.0.8-14
- Add Requires(post) for nss-tools, gencert needs it (#652007)

* Wed Mar  2 2011 Rob Crittenden <rcritten@redhat.com> - 1.0.8-13
- Lock around the pipe to nss_pcache for retrieving the token PIN
  (#677701)

* Tue Feb 08 2011 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.0.8-12
- Rebuilt for https://fedoraproject.org/wiki/Fedora_15_Mass_Rebuild

* Wed Jan 12 2011 Rob Crittenden <rcritten@redhat.com> - 1.0.8-11
- Use memmove in place of memcpy since the buffers can overlap (#669118)

* Wed Sep 29 2010 jkeating - 1.0.8-10
- Rebuilt for gcc bug 634757

* Thu Sep 23 2010 Rob Crittenden <rcritten@redhat.com> - 1.0.8-9
- Revert mod_nss-wouldblock patch
- Reset NSPR error before calling PR_Read(). This should fix looping
  in #620856

* Fri Sep 17 2010 Rob Crittenden <rcritten@redhat.com> - 1.0.8-8
- Fix hang when handling large POST under some conditions (#620856)

* Tue Jun 22 2010 Rob Crittenden <rcritten@redhat.com> - 1.0.8-7
- Remove file Requires on libnssckbi.so (#601939)

* Fri May 14 2010 Rob Crittenden <rcritten@redhat.com> - 1.0.8-6
- Ignore SIGHUP in nss_pcache (#591889).

* Thu May 13 2010 Rob Crittenden <rcritten@redhat.com> - 1.0.8-5
- Use remote hostname set by mod_proxy to compare to CN in peer cert (#591224)

* Thu Mar 18 2010 Rob Crittenden <rcritten@redhat.com> - 1.0.8-4
- Patch to add configuration options for new NSS negotiation API (#574187)
- Add (pre) for Requires on httpd so we can be sure the user and group are
  already available
- Add file Requires on libnssckbi.so so symlink can't fail
- Use _sysconfdir macro instead of /etc
- Set minimum level of NSS to 3.12.6

* Mon Jan 25 2010 Rob Crittenden <rcritten@redhat.com> - 1.0.8-3
- The location of libnssckbi moved from /lib[64] to /usr/lib[64] (556744)

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
