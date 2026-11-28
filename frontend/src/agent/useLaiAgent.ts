// Hook React cho cuộc trò chuyện AG-UI: giữ lượt chat, các lần gọi công cụ, bước, state dùng chung.
import {useCallback, useRef, useState} from 'react';
import type {AgentSubscriber} from '@ag-ui/client';
import {createAgent, toolLabel, toolTarget, type Command, type LaiState} from './laiAgent';

export interface ToolCallView {
  id: string;
  name: string;
  label: string;
  args: string;
  target?: string;
  status: 'running' | 'complete' | 'error';
  result?: string;
}

export type Turn =
  | {id: string; role: 'user'; text: string}
  | {id: string; role: 'system'; text: string}
  | {id: string; role: 'assistant'; text: string; steps: string[]; calls: ToolCallView[]; error?: string; isDone: boolean};

const uid = () => Math.random().toString(36).slice(2, 10);

export function useLaiAgent() {
  const agentRef = useRef(createAgent());
  const [turns, setTurns] = useState<Turn[]>([]);
  const [state, setStateView] = useState<LaiState>({});
  const [isRunning, setRunning] = useState(false);

  const patchAssistant = (id: string, fn: (t: Extract<Turn, {role: 'assistant'}>) => Extract<Turn, {role: 'assistant'}>) =>
    setTurns(ts => ts.map(t => (t.id === id && t.role === 'assistant' ? fn(t) : t)));

  const send = useCallback(async (text: string, command: Command = {type: 'soi'}, echo = text) => {
    const agent = agentRef.current;
    const aid = `a-${uid()}`;
    setTurns(ts => [
      ...ts,
      ...(echo ? [{id: `u-${uid()}`, role: 'user' as const, text: echo}] : []),
      {id: aid, role: 'assistant', text: '', steps: [], calls: [], isDone: false},
    ]);
    if (text) agent.addMessage({id: `m-${uid()}`, role: 'user', content: text});
    setRunning(true);

    const subscriber: AgentSubscriber = {
      onStepStartedEvent: ({event}) => patchAssistant(aid, t => ({...t, steps: [...t.steps, event.stepName]})),
      onToolCallStartEvent: ({event}) =>
        patchAssistant(aid, t => ({
          ...t,
          calls: [...t.calls, {id: event.toolCallId, name: event.toolCallName, label: toolLabel(event.toolCallName), args: '', status: 'running'}],
        })),
      onToolCallArgsEvent: ({event, toolCallBuffer, toolCallName}) =>
        patchAssistant(aid, t => ({
          ...t,
          calls: t.calls.map(c =>
            c.id === event.toolCallId ? {...c, args: toolCallBuffer, target: toolTarget(toolCallName, toolCallBuffer)} : c,
          ),
        })),
      onToolCallResultEvent: ({event}) => {
        const content = typeof event.content === 'string' ? event.content : JSON.stringify(event.content);
        patchAssistant(aid, t => ({
          ...t,
          calls: t.calls.map(c =>
            c.id === event.toolCallId
              ? {...c, result: content, status: content.includes('"error"') ? 'error' : 'complete'}
              : c,
          ),
        }));
      },
      onTextMessageContentEvent: ({event}) => patchAssistant(aid, t => ({...t, text: t.text + event.delta})),
      onStateChanged: ({state: s}) => setStateView({...(s as LaiState)}),
      onRunErrorEvent: ({event}) => patchAssistant(aid, t => ({...t, error: event.message})),
      onRunFailed: ({error}) => patchAssistant(aid, t => ({...t, error: String(error)})),
    };

    try {
      await agent.runAgent({forwardedProps: {command}}, subscriber);
    } catch (e) {
      patchAssistant(aid, t => ({...t, error: t.error ?? String(e)}));
    } finally {
      patchAssistant(aid, t => ({...t, isDone: true}));
      setRunning(false);
    }
  }, []);

  /** Ghi lựa chọn của chủ shop vào state dùng chung (lượt chạy sau agent cũng thấy). */
  const setLocal = useCallback((patch: Partial<LaiState>) => {
    const agent = agentRef.current;
    const next = {...(agent.state as LaiState), ...patch};
    agent.setState(next);
    setStateView(next);
  }, []);

  const note = useCallback((text: string) => {
    setTurns(ts => [...ts, {id: `n-${uid()}`, role: 'system', text}]);
  }, []);

  return {turns, state, isRunning, send, setLocal, note};
}
