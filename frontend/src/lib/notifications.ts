// Browser notification utilities

// Check if notifications are enabled in settings
function areNotificationsEnabled(): boolean {
  if (typeof window === "undefined") return false;
  try {
    const stored = localStorage.getItem("intellistream_settings");
    if (stored) {
      const settings = JSON.parse(stored);
      return settings.notificationsEnabled !== false; // Default to true
    }
  } catch {
    // Ignore errors
  }
  return true;
}

// Check if browser supports notifications
function isNotificationSupported(): boolean {
  return typeof window !== "undefined" && "Notification" in window;
}

// Request notification permission
export async function requestNotificationPermission(): Promise<boolean> {
  if (!isNotificationSupported()) return false;

  if (Notification.permission === "granted") return true;
  if (Notification.permission === "denied") return false;

  const permission = await Notification.requestPermission();
  return permission === "granted";
}

// Show a notification if enabled and permitted
export async function showNotification(
  title: string,
  options?: NotificationOptions
): Promise<void> {
  if (!areNotificationsEnabled()) return;
  if (!isNotificationSupported()) return;

  // Check if page is focused - don't show if user is looking at the page
  if (document.hasFocus()) return;

  // Only show if we have permission
  if (Notification.permission !== "granted") {
    // Try to get permission
    const granted = await requestNotificationPermission();
    if (!granted) return;
  }

  try {
    const notification = new Notification(title, {
      icon: "/favicon.ico",
      badge: "/favicon.ico",
      ...options,
    });

    // Auto-close after 5 seconds
    setTimeout(() => notification.close(), 5000);

    // Focus window when notification is clicked
    notification.onclick = () => {
      window.focus();
      notification.close();
    };
  } catch {
    // Ignore notification errors
  }
}

// Show response complete notification
export function showResponseNotification(): void {
  showNotification("IntelliStream", {
    body: "Your response is ready!",
    tag: "response-complete", // Prevents duplicate notifications
  });
}

// Show error notification
export function showErrorNotification(errorMessage?: string): void {
  showNotification("IntelliStream - Error", {
    body: errorMessage || "An error occurred while processing your request.",
    tag: "response-error",
  });
}
