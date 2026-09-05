---
title: "Programming language"
source: "https://simple.wikipedia.org/wiki/Programming_language"
license: "CC BY-SA 4.0"
topic: "computers"
fetched: "2026-09-03"
---

A programming language is a type of written language that tells computers what to do. Languages are often of two types, compiled or interpreted. Examples of compiled languages are: C, C++, Rust, Swift, and V (Vlang). Examples of interpreted languages are: AutoHotkey, C#, Java, JavaScript, Python, and Ruby. Programming languages are used to write computer programs and computer software. A programming language is like a set of commands that tell the computer how to do things.
Usually, the programming language uses real words for some commands (e.g., "if… then… else…", "and", "or"), so that the language is easier for a human to understand. Like any normal language, many programming languages use punctuation. To make a program, a programmer writes commands in their chosen programming language and saves the commands to a text file. This text file is called source code. Some programming languages, such as Python and JavaScript, can be read by the computer right away. If not, the source code has to be compiled, which means that the computer translates the source code into another language (such as assembly language or machine language) that a computer can read, but which is much harder for a person to read.
Computer programs must be written very carefully. If a programmer makes mistakes, then the program might then stop working, which is called "crashing". When a program has a problem because of how the code was written, this is called a "bug". A very small mistake can cause very serious bugs.


Types of programming languages
There are many types of programming languages. Most programming languages do not follow one type alone, so it is difficult to assign a type for each language. The examples of each type are given in each section below because they are the best, well-known examples of that type.


High-level vs. low-level
High-level programming languages require less knowledge about the hardware compared to low-level programming languages. This is because high-level programming languages abstract away the hardware the program is running on. Many high-level languages require an interpreter to run the source code on the hardware in real time. On the other hand, low-level languages usually convert the whole source code to machine code before running, because the source code is so close to the hardware that it is easy to do so.


Declarative vs. Imperative programming
Declarative programming languages describe a "problem" but they usually do not say how the problem should be solved. The problem description uses logic, and "solving" the problem often looks like automatically proving a system of logical axioms. Examples for such programming languages are Prolog, XSLT, LISP and SQL.
Imperative programming languages describe a system of state changes. At the start, the program is in a certain state, and the computer is given steps to follow, in order to perform an action. Following the steps causes the program to "change state".
In general, declarative programming languages are safer and shorter. Imperative programming languages are more common, because they are easier to use.


Functional vs. Procedural
Functional programming looks at programming like a function in mathematics. The program receives input, together with some information, and uses this information to create output. It will not have a state in between, and it will also not change things that are not related to the computation.
Procedural programs specify or describe sets of steps or state changes.


Stack-based
Stack-based languages look at some of the program's memory like a stack of cards. There are very few things that can be done with a stack. A data item can be put on the top of the stack. This operation is generally called "push". A data item can be removed from the top of the stack.  This is called a "pop".  You can look at the item at the top of the stack without removing it.  This is called a "peek".
If a program is written as "push 5; push 3; add; pop;" it will put 5 on the top of the stack, put 3 on top of the 5, add the top two values (3 + 5 = 8), replace the 3 and 5 with the 8, and print the top (8). Examples for programming languages that are stack-based are the languages Postscript and Forth.


Object-oriented

Object-oriented programming languages place data and functions that change data into a single unit. This unit is called an "object". Objects can interact with each other and change another object's data. This is usually called encapsulation or information hiding. Most modern programming languages are object-oriented, or at least allow this style of programming. Examples of this are Java, Python, Ruby, C++, C# and other C languages.


Flow-oriented
Flow-oriented programming sees programming as connecting different components. These components send messages back and forth. A single component can be part of different "programs", without the need to be changed internally.


Scientific computing

Some languages above can be used for scientific computing. For example, C++ and Python are also used in this way. On the other hand, there are some languages that have scientific computing as their main purpose. The following are some examples:

MATLAB — made by MathWorks
GNU Octave, Scilab — open source versions of MATLAB
R (programming language) — widely used in the field of statistics
Wolfram Mathematica — made by Wolfram Research


Document creation
LaTeX and SATySFi are programming languages which helps document creation.


Rules
Every programming language has rules about what it can and can not do. These include:

Correct numbers (types of numbers, and how large or small the numbers can be)
Words (reserved words, case-sensitivity)
Limits on what the programming language can do
Most languages have official standards that define the rules of how to write the source code. Some programming languages have two or more standards. This can happen when a new standard replaces an old one. For example, the Perl 5 standard replaced Perl 4 in 1993. It can happen because two people made two standards at the same time. For example, there are several standards for APL.


Object-Oriented Programming
Object-Oriented Programming (sometimes shortened to OOP) is a form of programming where all parts of the program are objects. Objects are pieces of memory with the same structure that can be used again and again. A bank account, bitmap, or hero from a video game could all be objects within a program. Objects are made up of properties (pieces of information the object stores) and methods, which are things the object can do. A Dog object might have properties like height and hairColor. Its methods might include bark() and wagTail().
All objects are created from templates called classes. You can think of a class as a mold from which objects are made. The class defines all the properties and methods that its objects will have. Objects created from a class are called instances of the class. A class can extend another class, which means that it takes all the properties and methods of the class but can add its own.
Here is an example of what a class might look like in a programming language:

class Dog extends Mammal {

  // These are properties:
  String breed = "Collie"
  String type = "Herding Dog"

  // These are methods
  void wagTail() {
    //Do some wagging
  }

  void bark() {
    // Do the barking here
  }

}

Notice that the Dog class extends the Mammal class, so all dogs will have the properties of a mammal, like hairLength, and methods, like eat() or sleep().
Object-oriented programming is used in many of today's most popular programming languages, such as Java, C#, Objective-C, C++, Python, Ruby, Javascript, and ActionScript.


Examples


Example of Visual Basic
Here is a simple program written in Visual Basic (a language made by Microsoft):

This program asks the user their age and responds based on what the user typed. If the user typed something that is not a number, the program says so. If the user typed a number less than zero, the program says so. If the user says they are older than 100 years old, the program says "That's old!". If the user typed a correct age, the program says back to the user how old they are.


Example of Python
Here is a program that does the same thing as the program above, but in Python:


Example of C#
The same thing as the program above, but in C#:


Example of Haskell
The same thing again, but in Haskell:


References


Related pages
Algorithm
Formal language
List of programming languages
Programmer
Compiler
Computer programming
Programming paradigm
Pseudocode
