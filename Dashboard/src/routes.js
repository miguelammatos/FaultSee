/*!

=========================================================
* Light Bootstrap Dashboard React - v1.3.0
=========================================================

* Product Page: https://www.creative-tim.com/product/light-bootstrap-dashboard-react
* Copyright 2019 Creative Tim (https://www.creative-tim.com)
* Licensed under MIT (https://github.com/creativetimofficial/light-bootstrap-dashboard-react/blob/master/LICENSE.md)

* Coded by Creative Tim

=========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

*/
import Dashboard from "views/Dashboard.jsx";
import UserProfile from "views/UserProfile.jsx";
import TableList from "views/TableList.jsx";
import Typography from "views/Typography.jsx";
import Icons from "views/Icons.jsx";
import Maps from "views/Maps.jsx";
import Notifications from "views/Notifications.jsx";
import Upgrade from "views/Upgrade.jsx";
import Graph from "views/Graph.jsx";
import GraphContainers from "views/GraphContainers.jsx";
import Logs from "views/logs.jsx";
import GraphInstances from "views/GraphInstances.jsx"
const dashboardRoutes = [
  {
    path: "/instancesgraphs",
    name: "Instances Graph ",
    icon: "pe-7s-graph1 text-info",
    component: GraphInstances,
    layout: ""
  },
  {
    path: "/graphs",
    name: "Hosts Graphs",
    icon: "pe-7s-graph2 text-danger",
    component: Graph,
    layout: ""
  },

  {
    path: "/logs",
    name: "Logs",
    icon: "pe-7s-news-paper text-warning",
    component: Logs,
    layout: ""
  },
  {
    path: "/contaienrgraphs",
    name: "Container Graphs",
    icon: "pe-7s-graph2 text-success",
    component: GraphContainers,
    layout: ""
  },
  {
    path: "/anewendpoint",
    name: " ----------------------- ",
    icon: "pe-7s-more",
    component: Dashboard,
    layout: ""
  },
  {
    path: "/dashboard",
    name: "Dashboard",
    icon: "pe-7s-graph",
    component: Dashboard,
    layout: ""
  },
  {
    path: "/user",
    name: "User Profile",
    icon: "pe-7s-user",
    component: UserProfile,
    layout: ""
  },
  {
    path: "/table",
    name: "Table List",
    icon: "pe-7s-note2",
    component: TableList,
    layout: ""
  },
  {
    path: "/typography",
    name: "Typography",
    icon: "pe-7s-news-paper",
    component: Typography,
    layout: ""
  },
  {
    path: "/icons",
    name: "Icons",
    icon: "pe-7s-science",
    component: Icons,
    layout: ""
  },
  {
    path: "/maps",
    name: "Maps",
    icon: "pe-7s-map-marker",
    component: Maps,
    layout: ""
  },
  {
    path: "/notifications",
    name: "Notifications",
    icon: "pe-7s-bell",
    component: Notifications,
    layout: ""
  }
];

export default dashboardRoutes;
