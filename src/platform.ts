import type { API, DynamicPlatformPlugin, Logger, PlatformAccessory, PlatformConfig, Service, Characteristic } from 'homebridge';
import { Rpc3Client } from './rpc3-client';
import { Rpc3ControlConfig, withDefaults } from './settings';

const PLUGIN_NAME = 'homebridge-rpc3control';
const PLATFORM_NAME = 'RPC3Control';

type OutletState = { value: boolean; ts: number };

export class Rpc3Platform implements DynamicPlatformPlugin {
  private readonly Service: typeof Service;
  private readonly Characteristic: typeof Characteristic;
  private readonly accessories = new Map<string, PlatformAccessory>();
  private readonly client: Rpc3Client;
  private readonly cfg: ReturnType<typeof withDefaults>;
  private readonly states = new Map<number, OutletState>();
  private queue: Promise<void> = Promise.resolve();

  constructor(
    private readonly log: Logger,
    config: PlatformConfig,
    private readonly api: API,
  ) {
    this.Service = this.api.hap.Service;
    this.Characteristic = this.api.hap.Characteristic;

    this.cfg = withDefaults(config as Rpc3ControlConfig);
    this.client = new Rpc3Client(this.cfg.scriptPath, this.cfg.username);

    this.api.on('didFinishLaunching', () => {
      this.setupOutlets();
      this.setupRebootSwitches();
      setInterval(() => this.refreshAll().catch((err) => this.log.error(String(err))), this.cfg.pollIntervalMs);
    });
  }

  configureAccessory(accessory: PlatformAccessory): void {
    this.accessories.set(accessory.UUID, accessory);
  }

  private setupOutlets(): void {
    for (const outlet of this.cfg.outlets) {
      const uuid = this.api.hap.uuid.generate(`rpc3-outlet-${outlet.serial ?? `${this.cfg.name}-${outlet.id}`}`);
      const accessory = this.ensureAccessory(uuid, outlet.name, this.Service.Outlet);
      accessory.context.kind = 'outlet';
      accessory.context.id = outlet.id;

      const service = accessory.getService(this.Service.Outlet) ?? accessory.addService(this.Service.Outlet, outlet.name);
      service.getCharacteristic(this.Characteristic.On)
        .onSet(async (value) => this.setOutlet(outlet.id, Boolean(value)))
        .onGet(async () => this.getOutlet(outlet.id));
    }
  }

  private setupRebootSwitches(): void {
    for (const sw of this.cfg.rebootSwitches) {
      const uuid = this.api.hap.uuid.generate(`rpc3-reboot-${sw.serial ?? `${this.cfg.name}-${sw.id}`}`);
      const accessory = this.ensureAccessory(uuid, sw.name, this.Service.Switch);
      accessory.context.kind = 'reboot';
      accessory.context.id = sw.id;

      const service = accessory.getService(this.Service.Switch) ?? accessory.addService(this.Service.Switch, sw.name);
      service.getCharacteristic(this.Characteristic.On)
        .onSet(async (value) => {
          if (Boolean(value)) {
            await this.enqueue(() => this.client.setOutlet(sw.id, 'reboot'));
            setTimeout(() => service.updateCharacteristic(this.Characteristic.On, false), 300);
          }
        })
        .onGet(() => false);
    }
  }

  private ensureAccessory(uuid: string, displayName: string, serviceType: typeof Service.Outlet | typeof Service.Switch): PlatformAccessory {
    const existing = this.accessories.get(uuid);
    if (existing) {
      existing.displayName = displayName;
      this.api.updatePlatformAccessories([existing]);
      return existing;
    }
    const accessory = new this.api.platformAccessory(displayName, uuid);
    accessory.addService(serviceType, displayName);
    this.api.registerPlatformAccessories(PLUGIN_NAME, PLATFORM_NAME, [accessory]);
    this.accessories.set(uuid, accessory);
    return accessory;
  }

  private async setOutlet(id: number, value: boolean): Promise<void> {
    await this.enqueue(() => this.client.setOutlet(id, value ? 'on' : 'off'));
    this.states.set(id, { value, ts: Date.now() });
  }

  private async getOutlet(id: number): Promise<boolean> {
    const cached = this.states.get(id);
    if (cached && Date.now() - cached.ts <= this.cfg.cacheTtlMs) {
      return cached.value;
    }
    const value = await this.enqueue(() => this.client.getOutlet(id));
    this.states.set(id, { value, ts: Date.now() });
    return value;
  }

  private async refreshAll(): Promise<void> {
    for (const outlet of this.cfg.outlets) {
      const value = await this.getOutlet(outlet.id);
      const uuid = this.api.hap.uuid.generate(`rpc3-outlet-${outlet.serial ?? `${this.cfg.name}-${outlet.id}`}`);
      const accessory = this.accessories.get(uuid);
      const service = accessory?.getService(this.Service.Outlet);
      service?.updateCharacteristic(this.Characteristic.On, value);
    }
  }

  private enqueue<T>(fn: () => Promise<T>): Promise<T> {
    const work = this.queue.then(fn, fn);
    this.queue = work.then(() => undefined, () => undefined);
    return work;
  }
}
