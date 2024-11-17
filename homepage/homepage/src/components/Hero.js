import React from "react";

const Hero = () => {
  const handleStartMapping = () => {
    window.location.href = "http://localhost:8501/";
  };

  return (
    <div className="relative pt-32 pb-20 sm:pt-40 sm:pb-24 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="lg:grid lg:grid-cols-12 lg:gap-8">
          <div className="sm:text-center md:max-w-2xl md:mx-auto lg:col-span-6 lg:text-left">
            <h1>
              <span className="block text-base font-semibold text-indigo-600">
                Introducing mindflow
              </span>
              <span className="mt-1 block text-4xl tracking-tight font-bold sm:text-5xl xl:text-6xl">
                <span className="block text-gray-900">Transform your</span>
                <span className="block text-indigo-600">
                  learning experience
                </span>
              </span>
            </h1>
            <p className="mt-3 text-base text-gray-500 sm:mt-5 sm:text-xl lg:text-lg xl:text-xl">
              Create beautiful, interactive mind maps that help you learn faster
              and retain more. Perfect for students, teachers, and lifelong
              learners.
            </p>
            <div className="mt-8 sm:max-w-lg sm:mx-auto sm:text-center lg:text-left">
              <button
                onClick={handleStartMapping}
                className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-lg shadow-sm text-white bg-black hover:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
              >
                Start mapping for free
              </button>
            </div>
          </div>
          {/* Rest of the component remains the same */}
        </div>
      </div>
    </div>
  );
};

export default Hero;
