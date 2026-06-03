"""
```
### What is SignalR?

SignalR (specifically ASP.NET SignalR, though the concept is general) is a framework that simplifies adding **real-time web functionality** to applications.

1. **Real-Time:** It allows server code to push content to connected clients (like a web browser or your Python application) instantly as it happens, rather than the client having to constantly poll the server for new data.
    
2. **Persistent Connection:** It automatically manages persistent connections between the server and client, using WebSockets where available, and gracefully falling back to older techniques (like long polling) if necessary.
    
3. **Bi-directional:** It enables two-way communication, meaning the client can call methods on the server, and the server can call methods on the client.
    

### When is the Right Time to Use SignalR?

You use SignalR whenever you need **low-latency, asynchronous updates** from the server without the client repeatedly asking for them.

|**Scenario**|**When to Use SignalR**|**When to Use Standard REST (like /Analog/Table)**|
|---|---|---|
|**Data Nature**|Real-time, streaming, or rapidly changing data.|Historical, batch, or configuration data.|
|**Examples**|Live dashboards, instant alerts, chat applications, gaming, monitoring real-time SCADA events.|Retrieving a CSV report, fetching a page of historical measurements, updating account settings.|
|**Client Behavior**|The client passively listens for server pushes.|The client actively requests (pulls) data when needed.|

**In the context of your `MissionClient`:**

- **`login_via_signalr`** is intended to establish the connection necessary to listen to **live updates** (e.g., a pump turned on, a pressure sensor spike, a heart-beat signal) which arrive via a WebSocket channel.
    
- **`login_to_session`** is intended to get the Bearer Token needed to access the **historical REST endpoints** (like `/Analog/Table` and `/Download/AnalogDownload`) that fetch stored data.
```
"""
