import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { FileText, Loader2 } from "lucide-react";
import { Button, Input, Card } from "@/components/ui";
import { useAuth } from "@/contexts/AuthContext";

export function LoginPage() {
  const { login, register } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      if (mode === "login") await login(username, password);
      else await register(username, password);
      navigate("/");
    } catch (err: any) {
      setError(err.message ?? "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <Card className="w-full max-w-sm p-6">
        <div className="flex flex-col items-center text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary text-primary-foreground">
            <FileText className="h-6 w-6" />
          </div>
          <h1 className="mt-3 text-xl font-semibold">{mode === "login" ? "Welcome back" : "Create an account"}</h1>
          <p className="mt-1 text-sm text-muted-foreground">Sign in to keep your documents private to you.</p>
        </div>

        <form onSubmit={submit} className="mt-5 space-y-3">
          <Input placeholder="Username" value={username} onChange={(e) => setUsername(e.target.value)} required minLength={3} />
          <Input type="password" placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={4} />
          {error && <p className="text-sm text-destructive">{error}</p>}
          <Button type="submit" className="w-full" loading={loading}>
            {mode === "login" ? "Sign in" : "Create account"}
          </Button>
        </form>

        <div className="mt-4 text-center text-sm text-muted-foreground">
          {mode === "login" ? (
            <>No account?{" "}<button onClick={() => setMode("register")} className="text-primary hover:underline">Register</button></>
          ) : (
            <>Have an account?{" "}<button onClick={() => setMode("login")} className="text-primary hover:underline">Sign in</button></>
          )}
        </div>
        <div className="mt-4 text-center">
          <Link to="/" className="text-xs text-muted-foreground hover:underline">Continue without signing in →</Link>
        </div>
      </Card>
    </div>
  );
}
