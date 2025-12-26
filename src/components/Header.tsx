import React from "react";
import { Waves, Activity, Upload, Moon, Sun, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";

export const Header = () => {
    const [isDark, setIsDark] = React.useState(false);
    const [scrolled, setScrolled] = React.useState(false);

    React.useEffect(() => {
        const theme = localStorage.getItem('theme');
        const shouldBeDark = theme === 'dark' || (!theme && window.matchMedia('(prefers-color-scheme: dark)').matches);
        setIsDark(shouldBeDark);
        if (shouldBeDark) {
            document.documentElement.classList.add('dark');
        }

        const handleScroll = () => {
            setScrolled(window.scrollY > 20);
        };

        window.addEventListener('scroll', handleScroll);
        return () => window.removeEventListener('scroll', handleScroll);
    }, []);

    const toggleTheme = () => {
        const newTheme = !isDark;
        setIsDark(newTheme);
        if (newTheme) {
            document.documentElement.classList.add('dark');
            localStorage.setItem('theme', 'dark');
        } else {
            document.documentElement.classList.remove('dark');
            localStorage.setItem('theme', 'light');
        }
    };

    return (
        <header
            className={`sticky top-0 z-50 transition-all duration-500 ${scrolled
                ? 'glass-strong shadow-premium'
                : 'animated-gradient shadow-ocean'
                }`}
        >
            <div className="container mx-auto px-6 py-5">
                <div className="flex items-center justify-between">
                    {/* Logo Section */}
                    <div className="flex items-center space-x-4 group">
                        <div className="relative">
                            <div className="absolute inset-0 bg-accent/20 rounded-full blur-xl group-hover:blur-2xl transition-all duration-500 animate-pulse"></div>
                            <Waves className={`h-12 w-12 relative z-10 transition-all duration-500 ${scrolled ? 'text-primary' : 'text-primary-foreground'
                                } group-hover:scale-110 group-hover:rotate-12`} />
                            <div className="absolute -top-1 -right-1 h-5 w-5 bg-accent rounded-full animate-pulse shadow-glow">
                                <Sparkles className="h-3 w-3 text-white m-1" />
                            </div>
                        </div>
                        <div className="animate-slide-up">
                            <h1 className={`text-3xl font-bold transition-all duration-300 ${scrolled ? 'text-gradient' : 'text-primary-foreground'
                                }`}>
                                Ocean Intel Bot
                            </h1>
                            <p className={`text-sm font-medium transition-all duration-300 ${scrolled ? 'text-muted-foreground' : 'text-primary-foreground/90'
                                }`}>
                                AI-Powered Oceanographic Analysis
                            </p>
                        </div>
                    </div>

                    {/* Navigation */}
                    <nav className="flex items-center space-x-3 animate-fade-in">
                        <Button
                            variant="ghost"
                            size="lg"
                            className={`transition-all duration-300 hover-lift ${scrolled
                                ? 'text-foreground hover:bg-primary/10 hover:text-primary'
                                : 'text-primary-foreground hover:bg-primary-foreground/20'
                                }`}
                        >
                            <Activity className="h-5 w-5 mr-2" />
                            <span className="font-medium">Live Data</span>
                        </Button>

                        <Button
                            variant="ghost"
                            size="lg"
                            className={`transition-all duration-300 hover-lift ${scrolled
                                ? 'text-foreground hover:bg-primary/10 hover:text-primary'
                                : 'text-primary-foreground hover:bg-primary-foreground/20'
                                }`}
                        >
                            <Upload className="h-5 w-5 mr-2" />
                            <span className="font-medium">Upload</span>
                        </Button>

                        {/* Floating Theme Toggle */}
                        <Button
                            onClick={toggleTheme}
                            size="lg"
                            className={`relative overflow-hidden transition-all duration-500 hover-lift ${scrolled
                                ? 'ocean-gradient text-primary-foreground shadow-glow'
                                : 'bg-primary-foreground/20 text-primary-foreground hover:bg-primary-foreground/30'
                                }`}
                            title={isDark ? "Switch to light mode" : "Switch to dark mode"}
                        >
                            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent translate-x-[-200%] group-hover:translate-x-[200%] transition-transform duration-1000"></div>
                            {isDark ? (
                                <Sun className="h-5 w-5 relative z-10 transition-transform duration-500 hover:rotate-180" />
                            ) : (
                                <Moon className="h-5 w-5 relative z-10 transition-transform duration-500 hover:-rotate-12" />
                            )}
                        </Button>
                    </nav>
                </div>
            </div>

            {/* Animated Wave Border */}
            <div className="absolute bottom-0 left-0 right-0 h-1 overflow-hidden">
                <div className={`h-full transition-all duration-500 ${scrolled ? 'ocean-gradient' : 'bg-primary-foreground/30'
                    } animate-wave`}></div>
            </div>
        </header>
    );
};

export default Header;
