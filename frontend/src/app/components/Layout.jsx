import React, { useEffect, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Bell,
  ChevronLeft,
  ChevronRight,
  Clock,
  Database,
  LayoutDashboard,
  LogOut,
  Map,
  Menu,
  Radio,
  Search,
  Settings,
  ShieldCheck,
  Truck,
  User,
  Wifi,
  X,
} from 'lucide-react';
import { NavLink, useNavigate } from 'react-router-dom';
import api from '../services/api';

const nav = [
  ['/dashboard', 'Dashboard', LayoutDashboard],
  ['/monitoring', 'Live Monitoring', Map],
  ['/units', 'Mobile Units', Truck],
  ['/issues', 'Infrastructure Issues', AlertTriangle],
  ['/maintenance', 'Maintenance Priority', Activity],
  ['/analytics', 'Analytics', BarChart3],
];

export default function Layout({ children }) {
  const [collapsed, setCollapsed] = useState(false);
  const [mobile, setMobile] = useState(false);
  const [search, setSearch] = useState('');
  const [showSearch, setShowSearch] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [showProfile, setShowProfile] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);
  const [summary, setSummary] = useState(null);
  const [vehicles, setVehicles] = useState([]);
  const [issues, setIssues] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [backendError, setBackendError] = useState('');
  const [isBackendLoading, setIsBackendLoading] = useState(true);
  const [notifications, setNotifications] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [refreshRate, setRefreshRate] = useState('5');

  const navigate = useNavigate();

  useEffect(() => {
    let isMounted = true;
    const loadBackendStatus = async () => {
      try {
        const [nextSummary, nextVehicles, nextIssues, nextAlerts] = await Promise.all([
          api.getSummary(),
          api.getVehicles(),
          api.getIssues(),
          api.getAlerts(),
        ]);
        if (!isMounted) return;
        setSummary(nextSummary);
        setVehicles(nextVehicles);
        setIssues(nextIssues);
        setAlerts(nextAlerts);
        setBackendError('');
      } catch (requestError) {
        if (!isMounted) return;
        setBackendError(requestError.message);
        setSummary(null);
        setVehicles([]);
        setIssues([]);
        setAlerts([]);
      } finally {
        if (isMounted) setIsBackendLoading(false);
      }
    };

    loadBackendStatus();
    const interval = setInterval(loadBackendStatus, 10000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  const filteredResults =
    search.trim().length === 0
      ? []
      : [
          ...vehicles.map((vehicle) => ({
            name: vehicle.id,
            type: 'Mobile Unit',
            detail: `${vehicle.type} · ${vehicle.zone}`,
            route: '/units',
          })),
          ...issues.map((issue) => ({
            name: issue.title,
            type: 'Infrastructure Issue',
            detail: issue.location,
            route: '/issues',
          })),
          ...alerts.map((alert) => ({
            name: alert.title,
            type: 'Infrastructure Issue',
            detail: alert.location,
            route: '/issues',
          })),
        ].filter((item) => {
          const query = search.toLowerCase();
          return (
            item.name.toLowerCase().includes(query) ||
            item.type.toLowerCase().includes(query) ||
            item.detail.toLowerCase().includes(query)
          );
        });

  const handleSearchResult = (route) => {
    navigate(route);
    setSearch('');
    setShowSearch(false);
    setMobile(false);
  };

  const openSettings = () => {
    setShowSettings(true);
    setShowProfile(false);
    setShowNotifications(false);
    setMobile(false);
  };

  const openProfile = () => {
    setShowProfile((previous) => !previous);
    setShowNotifications(false);
  };

  const openNotifications = () => {
    setShowNotifications((previous) => !previous);
    setShowProfile(false);
  };

  return (
    <div className="min-h-screen bg-app text-slate-800">
      <aside
        className={`
          smart-sidebar
          fixed
          z-40
          inset-y-0
          left-0
          border-r
          transition-all
          duration-200
          ${collapsed ? 'w-20' : 'w-64'}
          ${mobile ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
        `}
      >
        <div className="flex h-full flex-col p-4">
          <div className="flex items-center justify-between px-2 py-2">

            <button
              onClick={() => navigate("/dashboard")}
              className="flex items-center gap-3"
            >
              <div
                className="
                  grid
                  h-10
                  w-10
                  place-items-center
                  rounded-xl
                  bg-blue-50
                  text-blue-600
                "
              >
                <Wifi size={22} />
              </div>

              {!collapsed && (
                <div className="text-left">

                  <div className="font-bold tracking-tight text-blue-950">
                    UrbanSense
                  </div>

                  <div className="text-[10px] font-medium tracking-wide text-slate-400">
                    SMART CITY INTELLIGENCE
                  </div>

                </div>
              )}
            </button>

            <button
              className="hidden text-slate-400 hover:text-blue-600 md:block"
              onClick={() => setCollapsed(!collapsed)}
            >
              {collapsed ? (
                <ChevronRight size={19} />
              ) : (
                <ChevronLeft size={19} />
              )}
            </button>

          </div>

          <div className="my-5 h-px bg-slate-200" />

          {!collapsed && (
            <div className="px-3 pb-2 text-[10px] font-bold uppercase tracking-widest text-slate-400">
              Operations
            </div>
          )}

          {/* NAVIGATION */}

          <nav className="space-y-1">

            {nav.map(([to, label, Icon]) => (
              <NavLink
                key={to}
                to={to}
                onClick={() => setMobile(false)}
                className={({ isActive }) =>
                  `
                  smart-nav
                  flex
                  items-center
                  gap-3
                  rounded-xl
                  px-3
                  py-3
                  text-sm
                  transition
                  ${isActive ? "smart-nav-active" : ""}
                  `
                }
              >
                <Icon size={18} />

                {!collapsed && (
                  <span>{label}</span>
                )}
              </NavLink>
            ))}

          </nav>

          {/* SYSTEM */}

          <div className="mt-auto">

            {!collapsed && (
              <div
                className="
                  mb-3
                  rounded-xl
                  border
                  border-emerald-100
                  bg-emerald-50
                  p-3
                "
              >
                <div className="flex items-center gap-2 text-xs font-semibold text-emerald-700">

                  <span
                    className="
                      h-2
                      w-2
                      rounded-full
                      bg-emerald-500
                    "
                  />

                  {backendError ? 'Backend Offline' : isBackendLoading ? 'Checking Backend' : 'Backend Connected'}

                </div>

                <div className="mt-1 text-[11px] text-slate-500">
                  {backendError
                    ? 'Live data is unavailable'
                    : `${summary?.active_units ?? 0} active · ${summary?.registered_units ?? 0} registered devices`}
                </div>

              </div>
            )}

            {/* SETTINGS */}

            <button
              onClick={openSettings}
              className="
                smart-nav
                flex
                w-full
                items-center
                gap-3
                rounded-xl
                px-3
                py-3
                text-sm
              "
            >
              <Settings size={18} />

              {!collapsed && (
                <span>Settings</span>
              )}
            </button>

          </div>

        </div>
      </aside>

      {/* ==================================================
          MAIN
      ================================================== */}

      <div
        className={`
          min-h-screen
          transition-all
          duration-200
          ${collapsed ? "md:pl-20" : "md:pl-64"}
        `}
      >

        {/* ==================================================
            HEADER
        ================================================== */}

        <header
          className="
            smart-header
            sticky
            top-0
            z-30
            flex
            h-16
            items-center
            gap-4
            border-b
            px-4
            md:px-7
          "
        >

          {/* MOBILE MENU */}

          <button
            className="text-slate-500 md:hidden"
            onClick={() => setMobile(!mobile)}
          >
            {mobile ? <X /> : <Menu />}
          </button>

          {/* SEARCH */}

          <div className="relative max-w-xl flex-1">

            <Search
              className="
                absolute
                left-3
                top-1/2
                -translate-y-1/2
                text-slate-400
              "
              size={17}
            />

            <input
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setShowSearch(true);
              }}
              onFocus={() => {
                if (search.trim()) {
                  setShowSearch(true);
                }
              }}
              onKeyDown={(e) => {

                if (e.key === "Escape") {
                  setSearch("");
                  setShowSearch(false);
                }

                if (
                  e.key === "Enter" &&
                  filteredResults.length > 0
                ) {
                  handleSearchResult(
                    filteredResults[0].route
                  );
                }

              }}
              placeholder="Search vehicles, issues, zones..."
              className="
                smart-search
                w-full
                rounded-xl
                py-2.5
                pl-10
                pr-3
                text-sm
                outline-none
              "
            />

            {/* SEARCH RESULTS */}

            {showSearch && search.trim() && (
              <div
                className="
                  absolute
                  left-0
                  right-0
                  top-12
                  z-[100]
                  overflow-hidden
                  rounded-xl
                  border
                  border-slate-200
                  bg-white
                  shadow-xl
                "
              >

                {filteredResults.length > 0 ? (
                  <>

                    <div
                      className="
                        border-b
                        bg-slate-50
                        px-4
                        py-2
                        text-[10px]
                        font-bold
                        uppercase
                        tracking-wider
                        text-slate-500
                      "
                    >
                      Search Results
                    </div>

                    {filteredResults
                      .slice(0, 6)
                      .map((item) => (
                        <button
                          key={`${item.name}-${item.type}`}
                          onClick={() =>
                            handleSearchResult(item.route)
                          }
                          className="
                            flex
                            w-full
                            items-center
                            gap-3
                            border-b
                            border-slate-100
                            px-4
                            py-3
                            text-left
                            hover:bg-blue-50
                          "
                        >

                          <div
                            className="
                              grid
                              h-8
                              w-8
                              place-items-center
                              rounded-lg
                              bg-blue-50
                              text-blue-600
                            "
                          >
                            {item.type === "Mobile Unit" ? (
                              <Truck size={16} />
                            ) : item.type ===
                              "Infrastructure Issue" ? (
                              <AlertTriangle size={16} />
                            ) : (
                              <Map size={16} />
                            )}
                          </div>

                          <div className="min-w-0 flex-1">

                            <div
                              className="
                                truncate
                                text-sm
                                font-semibold
                                text-slate-800
                              "
                            >
                              {item.name}
                            </div>

                            <div
                              className="
                                truncate
                                text-xs
                                text-slate-500
                              "
                            >
                              {item.detail}
                            </div>

                          </div>

                          <span
                            className="
                              text-[10px]
                              font-medium
                              text-blue-600
                            "
                          >
                            {item.type}
                          </span>

                        </button>
                      ))}

                  </>
                ) : (
                  <div className="px-4 py-6 text-center">

                    <Search
                      size={22}
                      className="mx-auto text-slate-300"
                    />

                    <div className="mt-2 text-sm font-semibold text-slate-700">
                      No results found
                    </div>

                    <div className="mt-1 text-xs text-slate-400">
                      Try a vehicle ID, issue, or zone.
                    </div>

                  </div>
                )}

              </div>
            )}

          </div>

          {/* ACTIVE NODES */}

          <div
            className="
              smart-online
              hidden
              items-center
              rounded-lg
              border
              px-3
              py-2
              text-xs
              sm:flex
            "
          >
            <span
              className={`mr-2 inline-block h-2 w-2 rounded-full ${
                backendError ? 'bg-red-500' : 'smart-online-dot'
              }`}
            />

            {isBackendLoading
              ? 'Checking backend…'
              : backendError
                ? 'Backend offline'
                : `${summary?.active_units ?? 0} nodes active`}

          </div>

          {/* NOTIFICATION */}

          <div className="relative">

            <button
              onClick={openNotifications}
              className="
                relative
                hidden
                rounded-lg
                p-2
                text-slate-500
                hover:bg-slate-100
                hover:text-blue-600
                sm:block
              "
              title="Notifications"
            >

              <Bell size={19} />

              {alerts.length > 0 && (
                <span
                  className="
                    absolute
                    right-0.5
                    top-0.5
                    grid
                    h-4
                    min-w-4
                    place-items-center
                    rounded-full
                    bg-red-500
                    px-1
                    text-[9px]
                    font-bold
                    text-white
                  "
                >
                  {alerts.length}
                </span>
              )}

            </button>

            {/* NOTIFICATION PANEL */}

            {showNotifications && (
              <div
                className="
                  absolute
                  right-0
                  top-12
                  z-[150]
                  w-80
                  overflow-hidden
                  rounded-xl
                  border
                  border-slate-200
                  bg-white
                  shadow-xl
                "
              >

                <div
                  className="
                    flex
                    items-center
                    justify-between
                    border-b
                    border-slate-200
                    px-4
                    py-3
                  "
                >

                  <div className="text-sm font-bold text-slate-800">
                    Notifications
                  </div>

                  <span className="text-xs text-red-500">
                    {alerts.length} {alerts.length === 1 ? 'alert' : 'alerts'}
                  </span>

                </div>

                <div className="p-2">
                  {backendError ? (
                    <p className="p-3 text-sm text-red-600">
                      Unable to load backend alerts: {backendError}
                    </p>
                  ) : alerts.length === 0 ? (
                    <p className="p-3 text-sm text-slate-500">
                      No recent sensor alerts.
                    </p>
                  ) : alerts.map((alert) => {
                    const isHighSeverity =
                      alert.alert_type === 'HIGH_TEMPERATURE' ||
                      alert.alert_type === 'POTENTIAL_POTHOLE' ||
                      alert.severity === 'CRITICAL' ||
                      alert.severity === 'HIGH';
                    return (
                      <button
                        key={alert.id}
                        onClick={() => {
                          setShowNotifications(false);
                          navigate('/issues');
                        }}
                        className={`flex w-full gap-3 rounded-lg p-3 text-left ${
                          isHighSeverity ? 'hover:bg-red-50' : 'hover:bg-amber-50'
                        }`}
                      >
                        <div
                          className={`grid h-8 w-8 shrink-0 place-items-center rounded-lg ${
                            isHighSeverity ? 'bg-red-50 text-red-600' : 'bg-amber-50 text-amber-600'
                          }`}
                        >
                          {isHighSeverity ? <AlertTriangle size={16} /> : <Activity size={16} />}
                        </div>
                        <div>
                          <div className="text-sm font-semibold text-slate-800">{alert.title}</div>
                          <div className="text-xs text-slate-500">
                            {alert.alert_type === 'HIGH_TEMPERATURE'
                              ? `${alert.temperature_c} °C · ${alert.location}`
                              : alert.location}
                          </div>
                          {alert.alert_type === 'POTENTIAL_IMPACT' && (
                            <div className="text-[10px] text-slate-500">
                              {alert.impact_peak_g?.toFixed(2) ?? '—'} g · automatic decision: {alert.decision}
                            </div>
                          )}
                          {alert.alert_type === 'POTENTIAL_POTHOLE' && (
                            <div className="text-[10px] text-slate-500">
                              {alert.pothole_confidence ?? '—'}% motion confidence · decision: {alert.decision}
                            </div>
                          )}
                          {alert.alert_type === 'MANUAL_SIGNAL' && (
                            <div className="text-[10px] text-slate-500">
                              Automatic decision: {alert.decision}
                            </div>
                          )}
                          <div className="mt-1 text-[10px] text-slate-400">{alert.time}</div>
                        </div>
                      </button>
                    );
                  })}
                </div>

              </div>
            )}

          </div>

          {/* =================================================
              ADMIN PROFILE BUTTON
          ================================================= */}

          <div className="relative">

            <button
              onClick={openProfile}
              className="
                grid
                h-10
                w-10
                place-items-center
                rounded-full
                bg-blue-700
                text-sm
                font-bold
                text-white
                shadow-sm
                transition
                hover:bg-blue-800
                focus:outline-none
                focus:ring-2
                focus:ring-blue-200
              "
              title="Open profile"
            >
              AD
            </button>

            {/* PROFILE DROPDOWN */}

            {showProfile && (
              <div
                className="
                  absolute
                  right-0
                  top-12
                  z-[150]
                  w-64
                  overflow-hidden
                  rounded-xl
                  border
                  border-slate-200
                  bg-white
                  shadow-xl
                "
              >

                {/* PROFILE HEADER */}

                <div
                  className="
                    border-b
                    border-slate-200
                    px-4
                    py-4
                  "
                >

                  <div className="flex items-center gap-3">

                    <div
                      className="
                        grid
                        h-11
                        w-11
                        place-items-center
                        rounded-full
                        bg-blue-700
                        text-sm
                        font-bold
                        text-white
                      "
                    >
                      AD
                    </div>

                    <div>

                      <div className="text-sm font-bold text-slate-800">
                        Admin
                      </div>

                      <div className="text-xs text-slate-500">
                        City Operator
                      </div>

                    </div>

                  </div>

                </div>

                {/* PROFILE OPTIONS */}

                <div className="p-2">

                  <button
                    onClick={() => {
                      sessionStorage.removeItem('urbansense_token');
                      setShowProfile(false);
                      alert(
                        "My Profile\n\nName: Admin\nRole: City Operator\nOrganization: Smart City Initiative"
                      );
                    }}
                    className="
                      flex
                      w-full
                      items-center
                      gap-3
                      rounded-lg
                      px-3
                      py-2.5
                      text-left
                      text-sm
                      text-slate-600
                      hover:bg-blue-50
                      hover:text-blue-700
                    "
                  >
                    <User size={17} />
                    My Profile
                  </button>

                  <button
                    onClick={openSettings}
                    className="
                      flex
                      w-full
                      items-center
                      gap-3
                      rounded-lg
                      px-3
                      py-2.5
                      text-left
                      text-sm
                      text-slate-600
                      hover:bg-blue-50
                      hover:text-blue-700
                    "
                  >
                    <Settings size={17} />
                    Account Settings
                  </button>

                  <div className="my-1 border-t border-slate-100" />

                  <button
                    onClick={() => {
                      setShowProfile(false);
                      setShowNotifications(false);
                      setShowSettings(false);
                      setSearch("");
                      setShowSearch(false);
                      setMobile(false);
                      navigate("/login");
                    }}
                    className="
                      flex
                      w-full
                      items-center
                      gap-3
                      rounded-lg
                      px-3
                      py-2.5
                      text-left
                      text-sm
                      text-red-600
                      hover:bg-red-50
                    "
                  >
                    <LogOut size={17} />
                    Sign Out
                  </button>

                </div>

              </div>
            )}

                    </div>

          {/* GOVERNMENT OF INDIA */}

          <div
            className="
              hidden
              h-10
              items-center
              gap-3
              border-l
              border-slate-200
              pl-4
              lg:flex
            "
          >

            {/* Government Emblem */}
            <div
              className="
                flex
                h-9
                w-8
                items-center
                justify-center
                text-[22px]
              "
              title="Government of India"
            >
              🦁
            </div>

            {/* Government Text */}
            <div className="border-l border-slate-200 pl-3">

              <div className="text-[11px] font-bold leading-tight text-slate-800">
                Smart City Initiative
              </div>

              <div className="text-[9px] leading-tight text-slate-500">
                Government of India
              </div>

            </div>

            {/* Indian Flag */}
            <div className="ml-1 flex h-5 w-6 flex-col overflow-hidden rounded-sm">

              <span className="h-1.5 bg-orange-500" />

              <span className="relative h-1.5 bg-white">
                <span className="absolute left-1/2 top-1/2 h-1 w-1 -translate-x-1/2 -translate-y-1/2 rounded-full border border-blue-800" />
              </span>

              <span className="h-1.5 bg-green-600" />

            </div>

          </div>

        </header>

        {/* ==================================================
            PAGE CONTENT
        ================================================== */}

        <main className="p-4 md:p-7">
          {children}
        </main>

      </div>

      {/* ==================================================
          SETTINGS MODAL
      ================================================== */}

      {showSettings && (
        <div
          className="
            fixed
            inset-0
            z-[2000]
            flex
            items-center
            justify-center
            bg-slate-900/30
            p-4
            backdrop-blur-[2px]
          "
          onClick={() => setShowSettings(false)}
        >

          <div
            className="
              w-full
              max-w-lg
              overflow-hidden
              rounded-2xl
              border
              border-slate-200
              bg-white
              shadow-2xl
            "
            onClick={(e) => e.stopPropagation()}
          >

            {/* MODAL HEADER */}

            <div
              className="
                flex
                items-center
                justify-between
                border-b
                border-slate-200
                px-6
                py-5
              "
            >

              <div className="flex items-center gap-3">

                <div
                  className="
                    grid
                    h-10
                    w-10
                    place-items-center
                    rounded-xl
                    bg-blue-50
                    text-blue-600
                  "
                >
                  <Settings size={20} />
                </div>

                <div>

                  <h2 className="text-lg font-bold text-blue-950">
                    System Settings
                  </h2>

                  <p className="text-xs text-slate-500">
                    Configure UrbanSense monitoring preferences
                  </p>

                </div>

              </div>

              <button
                onClick={() => setShowSettings(false)}
                className="
                  rounded-lg
                  p-2
                  text-slate-400
                  hover:bg-slate-100
                  hover:text-slate-700
                "
              >
                <X size={18} />
              </button>

            </div>

            {/* SETTINGS BODY */}

            <div className="space-y-5 p-6">

              {/* IoT STREAM */}

              <div
                className="
                  flex
                  items-center
                  justify-between
                  rounded-xl
                  border
                  border-slate-200
                  bg-slate-50
                  p-4
                "
              >

                <div className="flex items-center gap-3">

                  <div
                    className="
                      grid
                      h-9
                      w-9
                      place-items-center
                      rounded-lg
                      bg-emerald-50
                      text-emerald-600
                    "
                  >
                    <Radio size={18} />
                  </div>

                  <div>

                    <div className="text-sm font-semibold text-slate-800">
                      IoT Data Stream
                    </div>

                    <div className="text-xs text-slate-500">
                      Authenticated backend data
                    </div>

                  </div>

                </div>

                <div
                  className={`flex items-center gap-2 text-xs font-semibold ${
                    backendError ? 'text-red-600' : 'text-emerald-600'
                  }`}
                >
                  <span className={`h-2 w-2 rounded-full ${backendError ? 'bg-red-500' : 'bg-emerald-500'}`} />
                  {backendError ? 'Unavailable' : isBackendLoading ? 'Checking' : 'Connected'}
                </div>

              </div>

              {/* DATA MODE */}

              <div>

                <div className="mb-2 flex items-center gap-2">

                  <Database
                    size={16}
                    className="text-blue-600"
                  />

                  <label className="text-sm font-semibold text-slate-800">
                    Data Mode
                  </label>

                </div>

                <div className="rounded-lg border border-slate-300 bg-slate-50 px-3 py-2.5 text-sm text-slate-700">
                  Live backend API
                </div>

              </div>

              {/* AUTO REFRESH */}

              <div
                className="
                  flex
                  items-center
                  justify-between
                "
              >

                <div className="flex items-center gap-3">

                  <Clock
                    size={17}
                    className="text-blue-600"
                  />

                  <div>

                    <div className="text-sm font-semibold text-slate-800">
                      Auto Refresh
                    </div>

                    <div className="text-xs text-slate-500">
                      Refresh monitoring data automatically
                    </div>

                  </div>

                </div>

                <button
                  onClick={() =>
                    setAutoRefresh(!autoRefresh)
                  }
                  className={`
                    relative
                    h-6
                    w-11
                    rounded-full
                    transition
                    ${
                      autoRefresh
                        ? "bg-blue-600"
                        : "bg-slate-300"
                    }
                  `}
                >

                  <span
                    className={`
                      absolute
                      top-1
                      h-4
                      w-4
                      rounded-full
                      bg-white
                      shadow
                      transition
                      ${
                        autoRefresh
                          ? "left-6"
                          : "left-1"
                      }
                    `}
                  />

                </button>

              </div>

              {/* REFRESH RATE */}

              <div>

                <label className="mb-2 block text-sm font-semibold text-slate-800">
                  Refresh Interval
                </label>

                <select
                  value={refreshRate}
                  onChange={(e) =>
                    setRefreshRate(e.target.value)
                  }
                  disabled={!autoRefresh}
                  className="
                    w-full
                    rounded-lg
                    border
                    border-slate-300
                    bg-white
                    px-3
                    py-2.5
                    text-sm
                    text-slate-700
                    outline-none
                    disabled:bg-slate-100
                  "
                >
                  <option value="3">
                    Every 3 seconds
                  </option>

                  <option value="5">
                    Every 5 seconds
                  </option>

                  <option value="10">
                    Every 10 seconds
                  </option>

                  <option value="30">
                    Every 30 seconds
                  </option>
                </select>

              </div>

              {/* ALERTS */}

              <div
                className="
                  flex
                  items-center
                  justify-between
                "
              >

                <div className="flex items-center gap-3">

                  <div
                    className="
                      grid
                      h-9
                      w-9
                      place-items-center
                      rounded-lg
                      bg-amber-50
                      text-amber-600
                    "
                  >
                    <Bell size={17} />
                  </div>

                  <div>

                    <div className="text-sm font-semibold text-slate-800">
                      Infrastructure Alerts
                    </div>

                    <div className="text-xs text-slate-500">
                      Receive critical issue notifications
                    </div>

                  </div>

                </div>

                <button
                  onClick={() =>
                    setNotifications(!notifications)
                  }
                  className={`
                    relative
                    h-6
                    w-11
                    rounded-full
                    transition
                    ${
                      notifications
                        ? "bg-blue-600"
                        : "bg-slate-300"
                    }
                  `}
                >

                  <span
                    className={`
                      absolute
                      top-1
                      h-4
                      w-4
                      rounded-full
                      bg-white
                      shadow
                      transition
                      ${
                        notifications
                          ? "left-6"
                          : "left-1"
                      }
                    `}
                  />

                </button>

              </div>

              {/* PROTOTYPE STATUS */}

              <div
                className="
                  flex
                  items-center
                  gap-3
                  rounded-xl
                  border
                  border-blue-100
                  bg-blue-50
                  p-4
                "
              >

                <ShieldCheck
                  size={20}
                  className="text-blue-600"
                />

                <div>

                  <div className="text-sm font-semibold text-blue-900">
                    Prototype Environment
                  </div>

                  <div className="text-xs text-blue-700/70">
                    Current dashboard uses simulated IoT data.
                  </div>

                </div>

              </div>

            </div>

            {/* FOOTER */}

            <div
              className="
                flex
                justify-end
                gap-2
                border-t
                border-slate-200
                bg-slate-50
                px-6
                py-4
              "
            >

              <button
                onClick={() => setShowSettings(false)}
                className="
                  rounded-lg
                  border
                  border-slate-300
                  bg-white
                  px-4
                  py-2
                  text-sm
                  font-medium
                  text-slate-600
                  hover:bg-slate-100
                "
              >
                Cancel
              </button>

              <button
                onClick={() => setShowSettings(false)}
                className="
                  rounded-lg
                  bg-blue-600
                  px-4
                  py-2
                  text-sm
                  font-semibold
                  text-white
                  shadow-sm
                  hover:bg-blue-700
                "
              >
                Save Settings
              </button>

            </div>

          </div>

        </div>
      )}

    </div>
  );
}