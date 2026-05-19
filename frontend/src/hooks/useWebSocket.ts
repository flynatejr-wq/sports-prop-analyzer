"use client";
import { useEffect, useRef, useState } from "react";
import { propSocket } from "@/lib/websocket";
import type { Prop } from "@/lib/types";

export function useLiveProps() {
  const [liveProps, setLiveProps] = useState<Prop[]>([]);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    propSocket.connect();

    const unsub = propSocket.subscribe((msg) => {
      if (msg.type === "snapshot" || msg.type === "props_update") {
        setLiveProps(msg.data);
        setConnected(true);
      }
    });

    return () => {
      unsub();
    };
  }, []);

  return { liveProps, connected };
}
