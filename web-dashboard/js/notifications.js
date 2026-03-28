// ═══════════════════════════════════════════════════════════════
// NormClaim — WebSocket & Notification System
// ═══════════════════════════════════════════════════════════════

const NotificationStore = {
  _notifications: [],
  _unreadCount: 0,
  _listeners: [],

  getAll() { return this._notifications; },
  getUnreadCount() { return this._unreadCount; },

  add(notification) {
    this._notifications.unshift({
      id: notification.id || Date.now(),
      message: notification.message,
      claimId: notification.claimId,
      priority: notification.priority || 'info',
      read: false,
      timestamp: notification.timestamp || new Date().toISOString(),
    });
    if (this._notifications.length > 50) this._notifications.pop();
    this._unreadCount++;
    this._notify();
    showToast(notification.message, notification.priority === 'urgent' ? 'warning' : 'info');
  },

  markAllRead() {
    this._notifications.forEach(n => n.read = true);
    this._unreadCount = 0;
    this._notify();
  },

  subscribe(fn) { this._listeners.push(fn); },
  _notify() { this._listeners.forEach(fn => fn(this)); },
};

// WebSocket manager (gracefully degrades when server unavailable)
const SocketManager = {
  _ws: null,
  _claimRoom: null,
  _reconnectTimer: null,

  connect() {
    try {
      const wsUrl = (window.location.protocol === 'https:' ? 'wss://' : 'ws://') 
        + window.location.hostname + ':8000/notifications';
      this._ws = new WebSocket(wsUrl);

      this._ws.onopen = () => console.log('[WS] Connected');
      this._ws.onmessage = (evt) => {
        try {
          const data = JSON.parse(evt.data);
          this._handleEvent(data);
        } catch(e) {}
      };
      this._ws.onclose = () => {
        console.log('[WS] Disconnected, will retry in 10s');
        this._reconnectTimer = setTimeout(() => this.connect(), 10000);
      };
      this._ws.onerror = () => {};
    } catch(e) {
      console.log('[WS] Not available, running in offline mode');
    }
  },

  joinClaimRoom(claimId) {
    this._claimRoom = claimId;
    if (this._ws?.readyState === WebSocket.OPEN) {
      this._ws.send(JSON.stringify({ action: 'join', room: `claim:${claimId}` }));
    }
  },

  leaveClaimRoom() {
    if (this._claimRoom && this._ws?.readyState === WebSocket.OPEN) {
      this._ws.send(JSON.stringify({ action: 'leave', room: `claim:${this._claimRoom}` }));
    }
    this._claimRoom = null;
  },

  disconnect() {
    clearTimeout(this._reconnectTimer);
    this._ws?.close();
  },

  _handleEvent(data) {
    switch(data.type) {
      case 'claim:status_changed':
        NotificationStore.add({ message: `Claim ${data.claimId} → ${STAGE_META[data.newStatus]?.label || data.newStatus}`, claimId: data.claimId, priority: 'info' });
        break;
      case 'claim:approval_needed':
        NotificationStore.add({ message: `Approval needed for claim ${data.claimId} (${data.stage})`, claimId: data.claimId, priority: 'urgent' });
        break;
      case 'settlement:utr_ready':
        NotificationStore.add({ message: `UTR ready: ${data.utrNumber} for claim ${data.claimId}`, claimId: data.claimId, priority: 'warning' });
        break;
      case 'notification:new':
        NotificationStore.add(data);
        break;
    }
  }
};
