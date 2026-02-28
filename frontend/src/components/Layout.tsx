import React from 'react';

interface LayoutProps {
    sidebarContent: React.ReactNode;
    children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ sidebarContent, children }) => {
    return (
        <div className="min-h-screen bg-slate-50 relative flex overflow-hidden font-sans text-slate-800">

            {/* Decorative Blobs for Light Glassmorphism Effect */}
            <div className="absolute top-[-10%] left-[-10%] w-96 h-96 bg-blue-300 rounded-full mix-blend-multiply filter blur-3xl opacity-40 animate-blob"></div>
            <div className="absolute top-[20%] right-[-5%] w-96 h-96 bg-cyan-300 rounded-full mix-blend-multiply filter blur-3xl opacity-40 animate-blob animation-delay-2000"></div>
            <div className="absolute bottom-[-10%] left-[20%] w-96 h-96 bg-indigo-300 rounded-full mix-blend-multiply filter blur-3xl opacity-40 animate-blob animation-delay-4000"></div>

            {/* Glass Sidebar */}
            <aside className="w-72 flex-shrink-0 z-10 m-4 rounded-2xl bg-white/40 backdrop-blur-md border border-white/60 shadow-lg shadow-slate-200/50 flex flex-col p-6">
                {sidebarContent}
            </aside>

            {/* Main Content Area */}
            <main className="flex-1 z-10 my-4 mr-4 flex flex-col min-h-0 bg-white/40 backdrop-blur-md border border-white/60 shadow-lg shadow-slate-200/50 rounded-2xl overflow-hidden">
                {children}
            </main>

        </div>
    );
};

export default Layout;
