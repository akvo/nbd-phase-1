declare namespace google.accounts.id {
  interface InitializeConfig {
    client_id: string;
    callback: (response: CredentialResponse) => void;
    auto_select?: boolean;
    cancel_on_tap_outside?: boolean;
    context?: "signin" | "signup" | "use";
  }

  interface CredentialResponse {
    credential: string;
    select_by?: string;
  }

  interface RenderButtonOptions {
    theme?: "outline" | "filled_blue" | "filled_black";
    size?: "large" | "medium" | "small";
    text?: "signin_with" | "signup_with" | "continue_with" | "signin";
    shape?: "rectangular" | "pill" | "circle" | "square";
    logo_alignment?: "left" | "center";
    width?: string | number;
    locale?: string;
  }

  function initialize(config: InitializeConfig): void;
  function renderButton(
    element: HTMLElement | null,
    options: RenderButtonOptions
  ): void;
  function prompt(): void;
  function disableAutoSelect(): void;
  function revoke(hint: string, callback: () => void): void;
}

interface Window {
  google?: {
    accounts: {
      id: typeof google.accounts.id;
    };
  };
}
