import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import wsService from '../services/websocket';

const SessionContext = createContext(null);

export function SessionProvider({ children }) {
  const [activeSession, setActiveSession] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [events, setEvents] = useState([]);
  const [students, setStudents] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const [connectionError, setConnectionError] = useState(null);
  const maxEvents = 100;
  const eventListenersRef = useRef([]);

  // Setup WebSocket listeners
  const setupListeners = useCallback(() => {
    // Clear existing listeners
    eventListenersRef.current.forEach((unsubscribe) => unsubscribe());
    eventListenersRef.current = [];

    // Session metrics update
    const unsubMetrics = wsService.on('session_metrics', (data) => {
      setMetrics(data.metrics);
    });
    eventListenersRef.current.push(unsubMetrics);

    // New event
    const unsubEvent = wsService.on('new_event', (data) => {
      setEvents((prev) => {
        const updated = [data.event, ...prev];
        return updated.slice(0, maxEvents);
      });
    });
    eventListenersRef.current.push(unsubEvent);

    // Student detected
    const unsubStudent = wsService.on('student_detected', (data) => {
      setStudents((prev) => {
        const exists = prev.find((s) => s.studentId === data.student.studentId);
        if (exists) {
          return prev.map((s) =>
            s.studentId === data.student.studentId ? { ...s, ...data.student } : s
          );
        }
        return [...prev, data.student];
      });
    });
    eventListenersRef.current.push(unsubStudent);

    // Student update
    const unsubStudentUpdate = wsService.on('student_update', (data) => {
      setStudents((prev) =>
        prev.map((s) =>
          s.studentId === data.student.studentId ? { ...s, ...data.student } : s
        )
      );
    });
    eventListenersRef.current.push(unsubStudentUpdate);

    // Disconnection
    const unsubDisconnect = wsService.on('disconnected', () => {
      setIsConnected(false);
    });
    eventListenersRef.current.push(unsubDisconnect);

    // Reconnection failed
    const unsubReconnectFailed = wsService.on('reconnect_failed', () => {
      setConnectionError('Failed to reconnect to session');
    });
    eventListenersRef.current.push(unsubReconnectFailed);
  }, []);

  // Connect to session
  const connectToSession = useCallback(
    async (sessionId) => {
      try {
        setConnectionError(null);
        await wsService.connect(sessionId);
        setIsConnected(true);
        setupListeners();
      } catch (error) {
        setConnectionError(error.message);
        setIsConnected(false);
        throw error;
      }
    },
    [setupListeners]
  );

  // Disconnect from session
  const disconnectFromSession = useCallback(() => {
    eventListenersRef.current.forEach((unsubscribe) => unsubscribe());
    eventListenersRef.current = [];
    wsService.disconnect();
    setIsConnected(false);
    setActiveSession(null);
    setMetrics(null);
    setEvents([]);
    setStudents([]);
  }, []);

  // Start monitoring session
  const startMonitoring = useCallback(
    async (session) => {
      setActiveSession(session);
      setEvents([]);
      setStudents([]);
      setMetrics(null);
      await connectToSession(session._id);
    },
    [connectToSession]
  );

  // Stop monitoring
  const stopMonitoring = useCallback(() => {
    disconnectFromSession();
  }, [disconnectFromSession]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnectFromSession();
    };
  }, [disconnectFromSession]);

  const value = {
    activeSession,
    metrics,
    events,
    students,
    isConnected,
    connectionError,
    startMonitoring,
    stopMonitoring,
    connectToSession,
    disconnectFromSession,
  };

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession() {
  const context = useContext(SessionContext);
  if (!context) {
    throw new Error('useSession must be used within a SessionProvider');
  }
  return context;
}

export default SessionContext;
