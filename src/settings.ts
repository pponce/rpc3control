export interface Rpc3OutletConfig {
  id: number;
  name: string;
  serial?: string;
}

export interface Rpc3RebootSwitchConfig {
  id: number;
  name: string;
  serial?: string;
}

export interface Rpc3ControlConfig {
  platform: string;
  name: string;
  scriptPath?: string;
  username?: string;
  pollIntervalMs?: number;
  cacheTtlMs?: number;
  outlets: Rpc3OutletConfig[];
  rebootSwitches?: Rpc3RebootSwitchConfig[];
}

export function withDefaults(config: Rpc3ControlConfig): Required<Omit<Rpc3ControlConfig, 'rebootSwitches'>> & { rebootSwitches: Rpc3RebootSwitchConfig[] } {
  return {
    ...config,
    scriptPath: config.scriptPath ?? '/var/lib/homebridge/rpc3control',
    username: config.username ?? 'admin',
    pollIntervalMs: config.pollIntervalMs ?? 5000,
    cacheTtlMs: config.cacheTtlMs ?? 1500,
    rebootSwitches: config.rebootSwitches ?? [],
  };
}
