// The shapes that cross from Python to the window. Checked against app.js by
// `tsc --noEmit` (checkJs, strict), so a field read wrongly is a lint failure
// rather than an "undefined" on screen.

type Mode = "auto" | "video" | "audio" | "images" | "transcript" | "thumbnail";
type Status = "queued" | "running" | "paused" | "done" | "failed" | "cancelled";

interface Settings {
  strip_metadata: boolean;
  folder: string;
  audio_folder: string;
  picture_folder: string;
  text_folder: string;
  by_site: boolean;
  template: string;
  file_date: string;
  restrict_names: boolean;
  rename: string;
  mode: Mode;
  quality: string;
  container: string;
  codec: string;
  prefer_sdr: boolean;
  always_plays: boolean;
  audio_format: string;
  audio_quality: string;
  audio_lang: string;
  format: string;
  playlist: boolean;
  playlist_reverse: boolean;
  items: string;
  section: string;
  chapters: string;
  precise_cuts: boolean;
  subs: string;
  sub_langs: string;
  auto_subs: boolean;
  embed_thumbnail: boolean;
  square_cover: boolean;
  embed_metadata: boolean;
  embed_chapters: boolean;
  split_chapters: boolean;
  write_thumbnail: boolean;
  write_description: boolean;
  write_info_json: boolean;
  write_comments: boolean;
  max_comments: string;
  sponsorblock: string;
  sponsor_categories: string;
  music: boolean;
  live_from_start: boolean;
  wait_for_live: boolean;
  archive: boolean;
  ignore_archive: boolean;
  min_duration: string;
  max_duration: string;
  date_after: string;
  date_before: string;
  skip_shorts: boolean;
  skip_live: boolean;
  skip_members: boolean;
  title_match: string;
  title_skip: string;
  max_items: string;
  range: string;
  gallery_filter: string;
  write_metadata: boolean;
  zip: boolean;
  ugoira: string;
  preview_playback: string;
  background_play: boolean;
  media_controls: boolean;
  skip_back: number;
  skip_forward: number;
  cookies: string;
  cookie_file: string;
  proxy: string;
  rate: string;
  impersonate: string;
  politeness: string;
  fragments: number;
  retries: number;
  concurrency: number;
  auto_retry: boolean;
  trim_names: number;
  hours_from: string;
  hours_to: string;
  min_free_gb: number;
  after: string;
  run_after: string;
  ytdlp_args: string;
  gdl_args: string;
  clipboard: string;
  hotkey: boolean;
  notify: boolean;
  sound: boolean;
  close_to_tray: boolean;
  autostart: boolean;
  auto_update: boolean;
  ytdlp_channel: string;
  self_update: boolean;
  last_update: number;
}

type SettingKey = keyof Settings;
type SettingValue = Settings[SettingKey];

interface JobView {
  id: string;
  serial: number;
  url: string;
  mode: string;
  status: Status;
  title: string;
  item: string;
  thumb: string;
  site: string;
  tool: string;
  stage: string;
  pct: number | null;
  speed: number | null;
  eta: number | null;
  size: number | null;
  error: string;
  advice: string;
  said: string;
  added: number;
  finished: number | null;
  index: number | null;
  count: number | null;
  errors: number;
  sub: string;
  repairable: boolean;
  retry_at: number;
  attempts: number;
  job_kind: string;
  repeat: number;
  nfiles: number;
  first: string;
  video: string;
}

interface Tools {
  "yt-dlp"?: string | null;
  "gallery-dl"?: string | null;
  ffmpeg?: string | null;
  js?: string | null;
  encoder?: string;
  afterimage?: boolean;
  seen?: string[];
}

interface AppUpdate {
  version: string;
  state: string;
  latest: string | null;
  notes: string[];
  checked: number;
  error: string;
  installed: boolean;
}

interface Subscription {
  id: string;
  url: string;
  name: string;
  mode: string;
  every: number;
  start: string;
  since: string;
  enabled: boolean;
  overrides: Record<string, string | boolean>;
  checked: number;
  found: number;
  last_new: number;
  last_error: string;
}

interface State {
  jobs: JobView[];
  tools: Tools;
  updating: boolean;
  note: string;
  app: AppUpdate;
  reason: string;
  held: number;
  after_all: string;
  subs: Subscription[];
  next: number;
}

interface SignIn {
  site: string;
  saved: number;
  cookies: number;
}

interface Boot {
  settings: Settings;
  defaults: Settings;
  own_folders: Record<string, string>;
  browsers: string[];
  afterimage: boolean;
  data: string;
  version: string;
  presets: string[];
  builtin: string[];
  accounts: SignIn[];
}

interface FormatRow {
  id: string;
  ext: string;
  res: string;
  fps: number | null;
  vcodec: string;
  acodec: string;
  size: number | null;
  tbr: number | null;
  note: string;
  lang: string;
  spec: string;
}

interface Entry {
  title: string;
  duration: number | null;
  url: string;
  thumb: string;
  channel: string;
}

interface Chapter {
  title: string;
  start: number | null;
  end: number | null;
}

interface ProbeFailure {
  error: string;
  advice: string;
  before?: number | null;
}

interface VideoProbe {
  kind: "video" | "playlist";
  watch: string;
  listen: string;
  title: string;
  uploader: string;
  duration: number | null;
  site: string;
  thumb: string;
  date: string;
  views: number | null;
  live: string;
  count: number;
  entries: Entry[];
  formats: FormatRow[];
  chapters: Chapter[];
  languages: string[];
  file: string;
  folder: string;
  before: number | null;
}

interface GalleryProbe {
  kind: "gallery";
  title: string;
  uploader: string;
  site: string;
  count: number;
  more: boolean;
  children: number;
  previews: string[];
  before: number | null;
}

type Probe = ProbeFailure | VideoProbe | GalleryProbe;

interface Playlist {
  id: string;
  name: string;
  files: string[];
  at: number;
}

interface LibFile {
  path: string;
  serial?: number;
  uri: string;
  name: string;
  kind: "video" | "audio" | "image";
  /** A video that was downloaded as sound, which the phone saves with a black picture. */
  sound?: boolean;
  size: number;
  time: number;
  folder: string;
}

interface HistEntry {
  id: string;
  serial?: number;
  url: string;
  mode: string;
  title: string;
  site: string;
  tool: string;
  status: string;
  thumb: string;
  files: string[];
  nfiles: number;
  bytes: number;
  finished: number | null;
  said: string;
  errors?: number;
  sub: string;
}

interface HistoryData {
  entries: HistEntry[];
  stats: { done: number; failed: number; bytes: number; sites: [string, number][] };
}

interface SearchResult {
  title: string;
  url: string;
  duration: number | null;
  channel: string;
  views: number | null;
  thumb: string;
}

interface Archive {
  file: string;
  label: string;
  entries: number;
  tool: string;
}

interface SubForm {
  url: string;
  name: string;
  mode: string;
  every: number;
  start: string;
  overrides: Record<string, string | boolean>;
}

interface TextRemoval {
  ready: boolean;
  size: number;
}

/** A rectangle of the eraser's picture to redraw: the marked part, and the pixels when they changed. */
interface EraserPatch {
  x: number;
  y: number;
  w: number;
  h: number;
  mask: string;
  picture: string;
}

/** What an eraser call answers: a picture opened, a rectangle, a saved copy, nothing ({}) or a problem. */
interface EraserAnswer {
  width?: number;
  height?: number;
  picture?: string;
  x?: number;
  y?: number;
  w?: number;
  h?: number;
  mask?: string;
  path?: string;
  error?: string;
}

interface KeepsakeApi {
  boot(): Promise<Boot>;
  state(): Promise<State>;
  set_title(title: string): Promise<null>;
  window_command(name: "minimize" | "maximize" | "close"): Promise<null>;
  maximized(): Promise<boolean>;
  clipboard(): Promise<string[]>;
  save_settings(changes: Partial<Settings>): Promise<Settings>;
  reset_settings(): Promise<Settings>;
  apply_preset(name: string): Promise<Settings>;
  save_preset(name: string): Promise<string[]>;
  delete_preset(name: string): Promise<string[]>;
  export_settings(): Promise<boolean>;
  import_settings(): Promise<Settings | null>;
  add(text: string, mode: string | null, extra: Partial<Settings> | null): Promise<{ found: number; added: number; before: number }>;
  probe(url: string, mode: string): Promise<Probe>;
  search(query: string, source: string, count: number): Promise<{ results: SearchResult[]; error: string }>;
  log(id: string): Promise<string[]>;
  act(action: string, ids: string[]): Promise<null>;
  everything(action: string): Promise<null>;
  schedule(when: string): Promise<null>;
  after_all(action: string): Promise<string>;
  cancel_shutdown(): Promise<null>;
  repair(id: string): Promise<null>;
  library(): Promise<LibFile[]>;
  convert(path: string, how: string, start: number, end: number): Promise<string>;
  text_removal(): Promise<TextRemoval>;
  set_up_text_removal(): Promise<boolean>;
  forget_text_removal(): Promise<TextRemoval>;
  eraser_open(path: string): Promise<EraserAnswer>;
  eraser_suggest(): Promise<EraserAnswer>;
  eraser_stroke(points: number[], size: number, erase: boolean, snap: boolean): Promise<EraserAnswer>;
  eraser_remove(): Promise<EraserAnswer>;
  eraser_undo(): Promise<EraserAnswer>;
  eraser_save(): Promise<EraserAnswer>;
  eraser_close(): Promise<null>;
  open_path(path: string): Promise<null>;
  reveal(path: string): Promise<"shown" | "folder" | "gone">;
  open_directory(path: string): Promise<boolean>;
  use_folders(which: string): Promise<Settings>;
  copy_path(path: string): Promise<boolean>;
  delete(path: string): Promise<boolean>;
  afterimage(path: string): Promise<null>;
  open_folder(which: string): Promise<null>;
  subtitles(path: string): Promise<{ label: string; vtt: string }[]>;
  playlists(): Promise<Playlist[]>;
  player_art(path: string): Promise<{ picture: string; wave: string }>;
  save_playlist(playlist: Partial<Playlist>): Promise<Playlist[]>;
  delete_playlist(id: string): Promise<Playlist[]>;
  plays_everywhere(path: string): Promise<boolean>;
  save_frame(path: string, seconds: number): Promise<string | null>;
  waveform(path: string): Promise<string>;
  thumbnail(path: string): Promise<string>;
  open_url(url: string): Promise<null>;
  pick_folder(start: string): Promise<string | null>;
  pick_file(purpose: string): Promise<string | null>;
  read_links(path: string): Promise<string>;
  history(): Promise<HistoryData>;
  forget(id: string): Promise<null>;
  clear_history(): Promise<null>;
  export_history(): Promise<boolean>;
  add_subscription(form: SubForm): Promise<boolean>;
  update_subscription(id: string, form: Partial<Subscription>): Promise<null>;
  remove_subscription(id: string): Promise<null>;
  check_subscription(id: string): Promise<null>;
  archives(): Promise<Archive[]>;
  archive_entries(name: string): Promise<string[]>;
  archive_forget(name: string, lines: string[]): Promise<number>;
  sign_in(url: string): Promise<boolean>;
  sign_ins(): Promise<SignIn[]>;
  forget_sign_in(site: string): Promise<SignIn[]>;
  update_tools(pin: string): Promise<boolean>;
  check_app_update(): Promise<AppUpdate>;
  restart(): Promise<null>;
}

interface Window {
  pywebview: { api: KeepsakeApi };
  keepsakeMedia?: (action: string, value?: number) => Promise<void>;
}
