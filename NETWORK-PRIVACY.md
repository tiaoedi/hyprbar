# Hyprbar network and privacy disclosure

This document describes network behavior visible in the staged Hyprbar source and documentation in this repository snapshot. It is a technical inventory, not a legal guarantee or a statement about third-party operators' retention or handling. Endpoints below are source request URLs; user- or sender-supplied destinations are identified as such. The download path follows HTTP redirects, and generic requests follow them when explicitly configured, so these URLs do not guarantee the final host in a redirect chain.

## Scope and network boundary

Hyprbar's shared `HttpClient` is used for several built-in HTTP transfers. Its offline-mode gate rejects its `download`, `post`, generic `request`, and streaming request paths before a transfer starts. The application sets this gate from `[shell].offline_mode` and updates it when configuration reloads. Enabling offline mode does not cancel transfers that were already active. A skipped request reports failure through its callback; this does not itself erase existing cached files or data. Consumers may continue to read local cached data or retain their in-memory state, depending on the service.

This is not a system-wide firewall. It does not govern browser navigation via `xdg-open`, traffic from other applications, unrelated operating-system services, or arbitrary network activity outside the shared client. In particular, plugin code can use facilities outside the shared HTTP client (see Plugins below); offline mode is not evidence that such unrelated traffic is blocked.

## Built-in service requests

### Endpoints inherited from upstream code

The following literal HTTPS endpoints are present in the staged code:

- `https://api.noctalia.dev/ip`: public/WAN IP lookup, disabled by default (`external_ip_enabled = false`). When enabled, Hyprbar sends a request to obtain the address for display in the Control Center/network tooltip. The remote service necessarily sees the connection's source IP. This path uses the shared client and is blocked by offline mode.
- `https://api.noctalia.dev/ping`: optional startup telemetry POST, disabled by default (`telemetry_enabled = false`). When enabled, source constructs a JSON payload containing a persistent random `instanceId`, version, compositor label, OS/distro label, rounded total RAM in GB, monitor width/height/scale entries, and UI scale. The ID is loaded from or created at the state directory's `instance.id` (normally `~/.local/state/hyprbar/instance.id`). This is a stable installation identifier, not an anonymous per-request random value. The POST uses the shared client and offline mode prevents it.
- `https://api.noctalia.dev/geolocate`: automatic approximate-location lookup when enabled. The request itself exposes the source IP to the endpoint. It uses the shared client, so `offline_mode` blocks this request.
- `https://api.noctalia.dev/geocode?city=…`: address/geocoding lookup. Hyprbar URL-encodes the configured address text into the query parameter, so that text is sent to the endpoint. Manually configured latitude/longitude avoids these location lookups. The request uses the shared client, so `offline_mode` blocks it.
- `https://api.noctalia.dev/palettes` and `https://api.noctalia.dev/palette/<name>`: community-palette catalog and palette data. Catalog and palette data are cached locally under the state directory's community-palettes area; cached palettes/catalog data can remain available when refresh fails or offline mode blocks a request.
- `https://api.noctalia.dev/templates`: community-template catalog. Hyprbar constructs selected manifest/file URLs beneath this base using catalog template IDs and relative file names; catalog metadata does not directly choose a hostname. The download path follows redirects, however, so the final host may differ. Catalog and template content are cached under the state directory's community-templates area. Local edits to cached template files are preserved rather than overwritten by sync in the documented cases.
- `https://api.noctalia.dev/v1/calendar/oauth/google/start`, `/result`, and `/refresh`: Google Calendar OAuth broker calls. They are made by Hyprbar's calendar client and are subject to shared-client offline mode. The broker returns an authorization URL for the browser handoff and brokers token exchange/refresh.

These hostnames and paths are inherited from the Noctalia codebase. This repository does not establish who currently operates the endpoints or how request data is retained, used, or disclosed. A link to an upstream privacy page is not a Hyprbar privacy policy or independent verification that it covers these requests.

### Weather

Hyprbar requests forecasts from `https://api.open-meteo.com/v1/forecast`, with `latitude` and `longitude` query parameters and forecast-field parameters. Those coordinates are the resolved weather location. The request goes directly from Hyprbar through its shared client; Open-Meteo therefore receives the request and connection source IP. Weather responses are cached locally and existing cached weather may be available when refresh is skipped or fails. Offline mode blocks the HTTP refresh, not local cache reads.

### Exchange rates

Currency-rate fetching is enabled by default (`shell.launcher.fetch_exchange_rates = true`). Hyprbar refreshes rates in the background via libqalculate's third-party online sources. The exact remote hosts are selected by that dependency and are not established as fixed Hyprbar URL literals here. Disabling the setting opts out of those refreshes; offline mode also skips refresh. The last locally cached rates remain usable for conversion.

### Calendar accounts and browser handoff

For Google Calendar, Hyprbar directly contacts the Noctalia OAuth broker endpoints listed above. It obtains an authorization URL and invokes the system browser (`xdg-open`) so the user can visit Google's consent page. Browser navigation and Google's own authorization traffic are browser-initiated, not HTTP transfers performed by Hyprbar's shared `HttpClient`. Google Calendar API calls then go directly to `https://www.googleapis.com/calendar/v3/users/me/calendarList` and `https://www.googleapis.com/calendar/v3/calendars/<calendar-id>/…`; requests carry OAuth authorization. The repository's calendar guide describes the permission as read-only (`calendar.readonly`), but this client does not set or validate the broker-side consent scope. Refresh tokens are stored locally in the desktop Secret Service; short-lived access tokens are held in memory. Offline mode prevents Hyprbar's shared-client calendar requests, but does not control the browser or other applications.

CalDAV and ICS endpoints are configured by the user, discovered from a user-configured server, or supplied by the calendar provider. Hyprbar connects directly to those account URLs; source does not imply one fixed host for generic CalDAV/ICS. The iCloud CalDAV discovery URL literal is `https://caldav.icloud.com/`. CalDAV credentials are stored through Secret Service or an explicitly configured password file, according to account configuration. Offline mode blocks the shared-client calendar network requests; the calendar service can display previously synced events from its encrypted on-disk cache when the storage key is available. Local vdir calendars are read locally.

## Remote images supplied by other software

MPRIS player metadata may contain album-art URLs. For HTTP(S) artwork, Hyprbar fetches the remote URL and caches the result locally; the destination host is determined by the active media player/metadata, not a fixed Hyprbar domain. Local artwork URLs/files do not imply a remote request. Remote-art downloads use the shared `HttpClient`, so offline mode blocks new downloads while already cached artwork can still be used.

Notifications may supply an icon as a URL. When the icon is an HTTP(S) URL, Hyprbar downloads and caches it; the notification sender chooses the URL and thus the destination host. Local paths and plain icon names do not cause that remote fetch. These downloads use the shared client and are blocked by offline mode; previously cached icons are distinct from new network fetches. Traffic, if any, made by the notification-sending application itself is outside Hyprbar's control.

## Community themes and templates

Hyprbar fetches the community palette catalog/data and community template catalog/manifests/files described above. These requests disclose ordinary connection metadata to the endpoint, and catalog/template identifiers and requested resource paths as part of the HTTP request. Templates are community-provided content and may include commands or hooks when applied; inspect and trust content before enabling it. Offline mode prevents shared-client HTTP fetching, while cached content can still be read/applied subject to feature configuration and availability.

## Plugins

The plugin runtime exposes network-capable operations including asynchronous downloads through the shared `HttpClient`; these are blocked when offline mode is enabled. The API also exposes streaming network functionality, likewise subject to the shared-client gate. Plugin installation/update can invoke `git` against a plugin source URL, and plugin code may invoke external processes or other facilities; those paths are not made safe or universally blocked merely by the shared HTTP-client gate. The staged plugin guide also describes Wallpaper Depth setup downloading a model from Hugging Face through an external `uv`-managed process; that plugin implementation is not included here, so its actual requests, redirect destinations, and any `offline_mode` check are not verified by this source review. Plugin destinations and remote URLs can be plugin-/user-configured. Treat plugins and their requested permissions/capabilities as executable third-party code, and review their source and configuration. This document does not assert that every plugin network-capable path is disabled by offline mode.

## Local state and cache

Network-derived data may be retained locally for continued use or reduced repeat fetching: this includes community catalogs/assets, weather snapshots, exchange rates, media artwork, notification icons, and synchronized calendar event data. Cache locations and lifetimes vary by feature; this disclosure does not infer deletion schedules or remote retention. Disabling a feature or enabling offline mode should not be interpreted as a promise that previously downloaded local cache files are erased.

## Verification basis

Statements were checked against the staged source and documentation, including `src/net/http_client.*`, application offline-mode wiring, location/weather/telemetry/external-IP services, calendar OAuth and clients, community palette/template services, MPRIS artwork and notification icon handling, launcher currency refresh, and scripting/plugin runtime code; relevant service and configuration documentation was also consulted. This is a source review only; no external validation or tests are claimed.
