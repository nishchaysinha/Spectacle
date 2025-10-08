RULES = {
    "javascript": {
        "files": ["package.json"],
        "pkgs": {
            "express": "Express",
            "next": "Next.js",
            "nestjs": "NestJS",
            "nuxt": "Nuxt.js",
            "angular": "Angular",
            "@angular/core": "Angular",
            "sveltekit": "SvelteKit",
            "koa": "Koa",
            "hapi": "hapi",
            "remix": "Remix",
            "fastify": "Fastify",
            "@adonisjs/core": "AdonisJS",
            "sails": "Sails",
            "@feathersjs/feathers": "FeathersJS",
            "loopback": "LoopBack",
            "@loopback/core": "LoopBack",
            "@redwoodjs/core": "RedwoodJS",
            "ember-cli": "Ember.js"
        }
    },
    "python": {
        "files": ["pyproject.toml", "requirements.txt"],
        "pkgs": {
            "django": "Django",
            "flask": "Flask",
            "fastapi": "FastAPI",
            "starlette": "Starlette",
            "tornado": "Tornado",
            "pyramid": "Pyramid",
            "bottle": "Bottle",
            "sanic": "Sanic",
            "falcon": "Falcon",
            "cherrypy": "CherryPy"
        }
    },
    "java": {
        "files": ["pom.xml", "build.gradle", "build.gradle.kts"],
        "markers": {
            "spring-boot-starter": "Spring Boot",
            "spring-framework": "Spring",
            "quarkus-": "Quarkus",
            "io.micronaut": "Micronaut",
            "vertx-": "Vert.x",
            "io.ktor": "Ktor",
            "io.javalin": "Javalin",
            "com.sparkjava": "Spark",
            "io.ratpack": "Ratpack",
            "io.dropwizard": "Dropwizard"
        }
    },
    "ruby": {
        "files": ["Gemfile"],
        "pkgs": {
            "rails": "Rails",
            "sinatra": "Sinatra",
            "hanami": "Hanami",
            "grape": "Grape"
        }
    },
    "php": {
        "files": ["composer.json"],
        "pkgs": {
            "laravel/framework": "Laravel",
            "symfony/framework-bundle": "Symfony",
            "codeigniter4/framework": "CodeIgniter",
            "cakephp/cakephp": "CakePHP",
            "yiisoft/yii2": "Yii",
            "slim/slim": "Slim",
            "zendframework/": "Zend (Laminas)",
            "laminas/": "Laminas"
        }
    },
    "go": {
        "files": ["go.mod"],
        "markers": {
            "github.com/gin-gonic/gin": "Gin",
            "github.com/labstack/echo": "Echo",
            "github.com/gofiber/fiber": "Fiber",
            "github.com/astaxie/beego": "Beego",
            "github.com/beego/beego": "Beego",
            "github.com/gobuffalo/buffalo": "Buffalo",
            "github.com/go-chi/chi": "Chi",
            "github.com/kataras/iris": "Iris",
            "github.com/gorilla/mux": "Gorilla Mux"
        }
    },
    "rust": {
        "files": ["Cargo.toml"],
        "pkgs": {
            "actix-web": "Actix",
            "rocket": "Rocket",
            "axum": "Axum",
            "warp": "Warp",
            "tide": "Tide"
        }
    },
    "csharp": {
        "files": ["*.csproj", "*.fsproj", "packages.config"],
        "markers": {
            "Microsoft.AspNetCore": "ASP.NET Core",
            "Nancy": "Nancy",
            "ServiceStack": "ServiceStack"
        }
    },
    "swift": {
        "files": ["Package.swift"],
        "markers": {
            "vapor": "Vapor",
            "kitura": "Kitura",
            "perfect": "Perfect"
        }
    },
    "elixir": {
        "files": ["mix.exs"],
        "pkgs": {
            "phoenix": "Phoenix"
        }
    }
}

TARGET_FILENAMES = {
    "package.json", "pyproject.toml", "requirements.txt",
    "pom.xml", "build.gradle", "build.gradle.kts",
    "Gemfile", "composer.json", "go.mod", "Cargo.toml",
    "*.csproj", "*.fsproj", "packages.config", "Package.swift", "mix.exs"
}
