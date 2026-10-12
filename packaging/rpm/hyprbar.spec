Name:           hyprbar
Version:        5.2.1
Release:        1%{?dist}
Summary:        A customizable desktop shell for Wayland
License:        MIT AND Apache-2.0
Source0:        %{name}-%{version}.tar.gz

BuildRequires:  gcc-c++
BuildRequires:  meson >= 1.1
BuildRequires:  ninja-build
BuildRequires:  pkgconf-pkg-config
BuildRequires:  wayland-devel
BuildRequires:  wayland-protocols-devel
BuildRequires:  libglvnd-devel
BuildRequires:  freetype-devel
BuildRequires:  fontconfig-devel
BuildRequires:  cairo-devel
BuildRequires:  pango-devel
BuildRequires:  harfbuzz-devel
BuildRequires:  libxkbcommon-devel
BuildRequires:  glib2-devel
BuildRequires:  libsecret-devel
BuildRequires:  libsodium-devel
BuildRequires:  sdbus-cpp-devel
BuildRequires:  pipewire-devel
BuildRequires:  wireplumber-devel
BuildRequires:  pam-devel
BuildRequires:  polkit-devel
BuildRequires:  libcurl-devel
BuildRequires:  libwebp-devel
BuildRequires:  libjxl-devel
BuildRequires:  libsndfile-devel
BuildRequires:  librsvg2-devel
BuildRequires:  libqalculate-devel
BuildRequires:  libxml2-devel
BuildRequires:  md4c-devel
BuildRequires:  tomlplusplus-devel
BuildRequires:  libical-devel
BuildRequires:  json-devel
BuildRequires:  stb_image_resize2-devel
BuildRequires:  stb_image_write-devel
BuildRequires:  jemalloc-devel

%description
Hyprbar is an independent Wayland desktop shell fork based on the Noctalia
v5.2.1 source. It provides panels, a launcher, notifications, wallpaper
controls, settings, and other shell features.

%prep
%autosetup -n %{name}-%{version}

%build
%meson -Dtests=enabled -Dnative_optimizations=false -Djemalloc=enabled
%meson_build

%check
mkdir -p _test-home/config _test-home/state _test-home/data _test-home/cache _test-runtime
chmod 0700 _test-home _test-home/config _test-home/state _test-home/data _test-home/cache _test-runtime
HYPRBAR_ASSETS_DIR="$PWD/assets" \
HOME="$PWD/_test-home" \
XDG_CONFIG_HOME="$PWD/_test-home/config" \
XDG_STATE_HOME="$PWD/_test-home/state" \
XDG_DATA_HOME="$PWD/_test-home/data" \
XDG_CACHE_HOME="$PWD/_test-home/cache" \
XDG_RUNTIME_DIR="$PWD/_test-runtime" \
%meson_test

%install
%meson_install

%{buildroot}%{_bindir}/hyprbar completions bash > bash-completion
%{buildroot}%{_bindir}/hyprbar completions zsh > zsh-completion
%{buildroot}%{_bindir}/hyprbar completions fish > fish-completion
install -D -m 0644 bash-completion %{buildroot}%{_datadir}/bash-completion/completions/hyprbar
install -D -m 0644 zsh-completion %{buildroot}%{_datadir}/zsh/site-functions/_hyprbar
install -D -m 0644 fish-completion %{buildroot}%{_datadir}/fish/vendor_completions.d/hyprbar.fish

install -D -m 0644 LICENSE %{buildroot}%{_licensedir}/%{name}/LICENSE
install -D -m 0644 third_party/wuffs/LICENSE-MIT %{buildroot}%{_licensedir}/%{name}/wuffs-LICENSE-MIT
install -D -m 0644 third_party/wuffs/LICENSE-APACHE %{buildroot}%{_licensedir}/%{name}/wuffs-LICENSE-APACHE
install -D -m 0644 third_party/material_color_utilities/LICENSE %{buildroot}%{_licensedir}/%{name}/material-color-utilities-LICENSE
install -D -m 0644 third_party/luau/lua_LICENSE.txt %{buildroot}%{_licensedir}/%{name}/luau-lua_LICENSE.txt
install -D -m 0644 third_party/luau/LICENSE.txt %{buildroot}%{_licensedir}/%{name}/luau-LICENSE.txt
install -D -m 0644 third_party/fzy/LICENSE %{buildroot}%{_licensedir}/%{name}/fzy-LICENSE
install -D -m 0644 assets/fonts/tabler-icons-license.txt %{buildroot}%{_licensedir}/%{name}/tabler-icons-LICENSE.txt

%files
%license %{_licensedir}/%{name}/LICENSE
%license %{_licensedir}/%{name}/wuffs-LICENSE-MIT
%license %{_licensedir}/%{name}/wuffs-LICENSE-APACHE
%license %{_licensedir}/%{name}/material-color-utilities-LICENSE
%license %{_licensedir}/%{name}/luau-lua_LICENSE.txt
%license %{_licensedir}/%{name}/luau-LICENSE.txt
%license %{_licensedir}/%{name}/fzy-LICENSE
%license %{_licensedir}/%{name}/tabler-icons-LICENSE.txt
%{_bindir}/hyprbar
%{_datadir}/applications/dev.hyprbar.Hyprbar.desktop
%{_datadir}/icons/hicolor/scalable/apps/hyprbar.svg
%{_datadir}/hyprbar/
%{_datadir}/bash-completion/completions/hyprbar
%{_datadir}/zsh/site-functions/_hyprbar
%{_datadir}/fish/vendor_completions.d/hyprbar.fish
