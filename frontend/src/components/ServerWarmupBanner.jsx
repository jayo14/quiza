import { useState, useEffect } from "react";
import { Loader2, CheckCircle2, CloudLightning } from "lucide-react";
import { API_BASE_URL } from "../config/api";
import "./ServerWarmupBanner.css";

export default function ServerWarmupBanner() {
  const [status, setStatus] = useState("idle"); // 'idle' | 'warming' | 'ready' | 'hidden'

  useEffect(() => {
    // Use API_BASE_URL/health (e.g. https://quiza-urmm.onrender.com/api/v1/health) to avoid adblocker filters targeting root /health
    const healthUrl = `${API_BASE_URL.replace(/\/$/, "")}/health`;

    let isMounted = true;
    let timerId = null;

    // Show warming notice if request takes longer than 1.8 seconds (indicates cold start)
    timerId = setTimeout(() => {
      if (isMounted && status === "idle") {
        setStatus("warming");
      }
    }, 1800);

    fetch(healthUrl)
      .then((res) => {
        if (res.ok) {
          clearTimeout(timerId);
          if (isMounted) {
            setStatus("ready");
            setTimeout(() => {
              if (isMounted) setStatus("hidden");
            }, 3000);
          }
        }
      })
      .catch(() => {
        // Ignored; app endpoints will handle operational retries
      });

    return () => {
      isMounted = false;
      if (timerId) clearTimeout(timerId);
    };
  }, []);

  if (status === "idle" || status === "hidden") return null;

  return (
    <div className={`server-warmup-banner server-warmup-banner--${status}`}>
      {status === "warming" && (
        <>
          <CloudLightning className="server-warmup-icon pulse" size={18} />
          <Loader2 className="server-warmup-spinner" size={16} />
          <span>Waking up cloud backend server (Render free tier may take ~30s on first load)...</span>
        </>
      )}

      {status === "ready" && (
        <>
          <CheckCircle2 className="server-warmup-icon success" size={18} />
          <span>Backend server active and ready!</span>
        </>
      )}
    </div>
  );
}
