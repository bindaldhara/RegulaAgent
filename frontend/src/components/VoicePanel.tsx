import {
  LiveKitRoom,
  RoomAudioRenderer,
  StartAudio,
  useConnectionState,
  useRemoteParticipants,
  useRoomContext,
} from "@livekit/components-react";
import { ConnectionState, DisconnectReason, RoomEvent } from "livekit-client";
import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { fetchVoiceStatus, fetchVoiceToken } from "../api/voice";
import type { AgentRunResponse, ChatHistoryTurn } from "../types/agent";
import { GlassCard } from "./GlassCard";

const DATA_TOPIC = "regula.agent";

interface VoicePanelProps {
  signedIn: boolean;
  consentGranted: boolean;
  conversationId: string | null;
  chatHistory: ChatHistoryTurn[];
  onAgentTurn: (payload: {
    userMessage: string;
    reply: string;
    conversationId?: string;
    run?: Partial<AgentRunResponse>;
  }) => void;
  disabled?: boolean;
  /** Renders Start/End voice beside Send; active session UI stays above the row. */
  footer?: (voiceControl: ReactNode) => ReactNode;
}

function VoiceControls({
  onDisconnect,
  agentConnected,
  liveTranscript,
  showEndButton = true,
}: {
  onDisconnect: () => void;
  agentConnected: boolean;
  liveTranscript: string;
  showEndButton?: boolean;
}) {
  const room = useRoomContext();
  const state = useConnectionState();
  const connected = state === ConnectionState.Connected;

  return (
    <div className="mt-2 space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <span
          className={`rounded-full px-2.5 py-0.5 text-[10px] font-medium uppercase tracking-wider ${
            connected
              ? "bg-emerald-500/20 text-emerald-300"
              : "bg-white/5 text-zinc-500"
          }`}
        >
          {connected ? "Mic connected" : "Connecting…"}
        </span>
        <span
          className={`rounded-full px-2.5 py-0.5 text-[10px] font-medium uppercase tracking-wider ${
            agentConnected
              ? "bg-violet-500/20 text-violet-200"
              : "bg-amber-500/15 text-amber-200"
          }`}
        >
          {agentConnected ? "Agent in room" : "Waiting for agent…"}
        </span>
        {showEndButton ? (
          <button
            type="button"
            onClick={() => {
              room.disconnect();
              onDisconnect();
            }}
            className="rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-zinc-300 hover:bg-white/10"
          >
            End voice
          </button>
        ) : null}
      </div>
      <div className="rounded-lg border border-white/5 bg-black/20 px-3 py-2">
        <p className="text-[10px] uppercase tracking-wider text-zinc-500">Heard</p>
        <p className="min-h-[1.25rem] text-sm text-zinc-200">
          {liveTranscript || "Speak after the greeting…"}
        </p>
      </div>
    </div>
  );
}

export function VoicePanel({
  signedIn,
  consentGranted,
  conversationId,
  chatHistory,
  onAgentTurn,
  disabled,
  footer,
}: VoicePanelProps) {
  const [voiceEnabled, setVoiceEnabled] = useState(false);
  const [session, setSession] = useState<{ token: string; url: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const [liveTranscript, setLiveTranscript] = useState("");
  const [agentName, setAgentName] = useState("regula-voice");
  const userEndedRef = useRef(false);
  const [linkDropped, setLinkDropped] = useState(false);

  useEffect(() => {
    fetchVoiceStatus()
      .then((s) => {
        setVoiceEnabled(s.enabled);
        if (s.agent_name) setAgentName(s.agent_name);
      })
      .catch(() => setVoiceEnabled(false));
  }, []);

  const startVoice = useCallback(async () => {
    if (!signedIn || starting || disabled) return;
    setError(null);
    setLiveTranscript("");
    setLinkDropped(false);
    userEndedRef.current = false;
    setStarting(true);
    try {
      const creds = await fetchVoiceToken({
        conversation_id: conversationId,
        chat_history: chatHistory,
      });
      setSession({ token: creds.token, url: creds.url });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start voice");
      setSession(null);
    } finally {
      setStarting(false);
    }
  }, [signedIn, starting, disabled, conversationId, chatHistory]);

  const endVoice = useCallback(() => {
    userEndedRef.current = true;
    setSession(null);
    setLiveTranscript("");
    setLinkDropped(false);
  }, []);

  const handleRoomDisconnected = useCallback(
    (reason?: DisconnectReason) => {
      if (userEndedRef.current) {
        endVoice();
        return;
      }
      setLinkDropped(true);
      if (reason === DisconnectReason.CLIENT_INITIATED) {
        setError("Voice link closed. Stay on this tab and click Start voice again if chat did not update.");
      }
    },
    [endVoice],
  );

  const voiceControl =
    !session ? (
      <button
        type="button"
        disabled={!signedIn || starting || disabled}
        onClick={() => void startVoice()}
        title={signedIn ? "Start voice (LiveKit)" : "Sign in to use voice"}
        className="shrink-0 rounded-full border border-violet-400/35 bg-violet-600/25 px-4 py-3 text-sm font-medium text-violet-100 hover:bg-violet-600/40 disabled:cursor-not-allowed disabled:opacity-40"
      >
        {starting ? "…" : "Voice"}
      </button>
    ) : (
      <button
        type="button"
        onClick={() => {
          userEndedRef.current = true;
          endVoice();
        }}
        className="shrink-0 rounded-full border border-white/15 bg-white/5 px-4 py-3 text-sm font-medium text-zinc-200 hover:bg-white/10"
      >
        End voice
      </button>
    );

  const sessionBlock = session ? (
    <div className="regula-voice-room mb-3 rounded-2xl border border-violet-400/20 bg-violet-950/20 p-3">
      <LiveKitRoom
        token={session.token}
        serverUrl={session.url}
        connect
        audio
        video={false}
        options={{ disconnectOnPageLeave: false }}
        onDisconnected={handleRoomDisconnected}
        className="regula-voice-room__inner"
      >
        <StartAudio label="Enable speaker" />
        <RoomAudioRenderer />
        <VoiceRoomDataBridge onAgentTurn={onAgentTurn} onTranscript={setLiveTranscript} />
        <VoiceSessionStatus
          liveTranscript={liveTranscript}
          agentName={agentName}
          onDisconnect={endVoice}
          showEndButton={!footer}
        />
      </LiveKitRoom>
    </div>
  ) : null;

  const hints = (
    <>
      {!signedIn && footer ? (
        <p className="mb-2 text-xs text-zinc-500">Sign in to use voice scheduling.</p>
      ) : null}
      {signedIn && !consentGranted ? (
        <p className="mb-2 text-xs text-amber-200/90">
          Enable scheduling consent in the panel to book or cancel by voice.
        </p>
      ) : null}
      {error ? <p className="mb-2 text-xs text-red-300">{error}</p> : null}
      {linkDropped ? (
        <p className="mb-2 text-xs text-amber-200/90">
          Connection dropped — check the chat for the agent reply, then start voice again if needed.
        </p>
      ) : null}
    </>
  );

  if (!voiceEnabled) {
    return footer ? <>{footer(null)}</> : null;
  }

  if (footer) {
    return (
      <>
        {hints}
        {sessionBlock}
        {footer(voiceControl)}
      </>
    );
  }

  return (
    <GlassCard className="mb-3 p-3" glow="violet">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-violet-200/90">Voice</p>
          <p className="text-[11px] text-zinc-500">LiveKit · same scheduling agent as chat</p>
        </div>
        {!session ? voiceControl : null}
      </div>
      {hints}
      {!session ? (
        <p className="mt-2 text-[11px] text-zinc-600">
          Voice worker must be running (service <code className="text-zinc-500">voice-worker</code> in
          docker compose).
        </p>
      ) : null}
      {sessionBlock}
    </GlassCard>
  );
}

function VoiceSessionStatus({
  liveTranscript,
  agentName,
  onDisconnect,
  showEndButton = true,
}: {
  liveTranscript: string;
  agentName: string;
  onDisconnect: () => void;
  showEndButton?: boolean;
}) {
  const remotes = useRemoteParticipants();
  const agentConnected = remotes.length > 0;
  const [showHint, setShowHint] = useState(false);

  useEffect(() => {
    if (agentConnected) {
      setShowHint(false);
      return;
    }
    const timer = window.setTimeout(() => setShowHint(true), 12_000);
    return () => window.clearTimeout(timer);
  }, [agentConnected]);

  return (
    <>
      <VoiceControls
        onDisconnect={onDisconnect}
        agentConnected={agentConnected}
        showEndButton={showEndButton}
        liveTranscript={liveTranscript}
      />
      {showHint && !agentConnected ? (
        <p className="mt-2 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-[11px] leading-relaxed text-amber-100">
          {import.meta.env.PROD ? (
            <>
              No voice agent in the room yet. Production voice runs on Render (
              <code className="text-amber-200">regula-agent-voice</code>); free instances sleep when
              idle — end voice, wait up to ~2 minutes, and try again. Agent must be{" "}
              <code className="text-amber-200">{agentName}</code>. See{" "}
              <code className="text-amber-200">docs/deployment.md</code>.
            </>
          ) : (
            <>
              No voice agent joined yet. Start the <strong>voice-worker</strong> container and check logs:{" "}
              <code className="text-amber-200">docker compose logs -f voice-worker</code>. It must register
              agent <code className="text-amber-200">{agentName}</code>. Check{" "}
              <code className="text-amber-200">GROQ_API_KEY</code> (free STT) in <code className="text-amber-200">.env</code> — see{" "}
              <code className="text-amber-200">docs/voice.md</code>.
            </>
          )}
        </p>
      ) : null}
    </>
  );
}

function VoiceRoomDataBridge({
  onAgentTurn,
  onTranscript,
}: {
  onAgentTurn: VoicePanelProps["onAgentTurn"];
  onTranscript: (text: string) => void;
}) {
  const room = useRoomContext();

  useEffect(() => {
    const handler = (
      payload: Uint8Array,
      _participant?: unknown,
      _kind?: unknown,
      topic?: string,
    ) => {
      if (topic && topic !== DATA_TOPIC) return;
      try {
        const text = new TextDecoder().decode(payload);
        const data = JSON.parse(text) as {
          type?: string;
          text?: string;
          final?: boolean;
          user_message?: string;
          reply?: string;
          conversation_id?: string;
          policy?: AgentRunResponse["policy"];
          intent?: AgentRunResponse["intent"];
          current_step?: AgentRunResponse["current_step"];
          run_id?: string;
          proposed_action?: AgentRunResponse["proposed_action"];
          tool_result?: AgentRunResponse["tool_result"];
          identity_status?: AgentRunResponse["identity_status"];
          consent_status?: AgentRunResponse["consent_status"];
        };

        if (data.type === "transcript" && data.text) {
          onTranscript(data.final ? data.text : `${data.text}…`);
          return;
        }

        if (data.type === "agent_greeting" && data.reply) {
          onAgentTurn({
            userMessage: "",
            reply: data.reply,
          });
          return;
        }

        if (data.type !== "agent_turn" || !data.user_message || !data.reply) return;
        onTranscript(data.user_message);
        onAgentTurn({
          userMessage: data.user_message,
          reply: data.reply,
          conversationId: data.conversation_id,
          run: {
            conversation_id: data.conversation_id as AgentRunResponse["conversation_id"],
            run_id: data.run_id,
            reply: data.reply,
            policy: data.policy ?? undefined,
            intent: data.intent ?? undefined,
            current_step: data.current_step,
            proposed_action: data.proposed_action,
            tool_result: data.tool_result,
            identity_status: data.identity_status,
            consent_status: data.consent_status,
          },
        });
      } catch {
        /* ignore */
      }
    };

    room.on(RoomEvent.DataReceived, handler);
    return () => {
      room.off(RoomEvent.DataReceived, handler);
    };
  }, [room, onAgentTurn, onTranscript]);

  return null;
}
