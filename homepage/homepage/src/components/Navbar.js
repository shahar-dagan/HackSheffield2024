import React from "react";

const Navbar = () => {
  return (
    <nav className="fixed w-full bg-white/80 backdrop-blur-md z-50 border-b border-gray-100">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-20">
          <div className="flex items-center">
            <div className="text-2xl font-bold bg-gradient-to-r from-indigo-500 to-purple-500 text-transparent bg-clip-text">
              mindflow
            </div>
          </div>
          <div className="hidden md:flex items-center space-x-8">
            <a href="#" className="text-gray-600 hover:text-gray-900">
              Products
            </a>
            <a href="#" className="text-gray-600 hover:text-gray-900">
              Solutions
            </a>
            <a href="#" className="text-gray-600 hover:text-gray-900">
              Resources
            </a>
            <a href="#" className="text-gray-600 hover:text-gray-900">
              Pricing
            </a>
            <button className="px-5 py-2.5 bg-black text-white rounded-lg text-sm font-medium hover:bg-gray-800">
              Get Started
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
